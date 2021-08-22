from re import sub
from json import loads as parse_json
from typing import Dict, List, Tuple
from datetime import datetime as dtime
from datetime import timedelta

from tqdm import tqdm
from trueskill import Rating, TrueSkill
from dateutil.parser import isoparse
from currency_converter import CurrencyConverter

from requester import cache, get_content

# Cache events and matches that are older than this.
CACHE_TIME: dtime = dtime.now().replace(tzinfo=None) - timedelta(days=30)


cc: CurrencyConverter = CurrencyConverter()


def event_filter(event: Dict) -> bool:
    if "groups" in event:
        groups: List[str] = event["groups"]
        if "grid" in groups:
            return False
        if "rlcs" in groups or "rlrs" in groups:
            return True
    if "prize" in event:
        prize: Dict = event["prize"]
        prize_pool: int = prize["amount"]
        if prize["currency"] != "USD":
            prize_pool: int = cc.convert(prize["amount"], prize["currency"], "USD")
        return prize_pool >= 50000
    return False


def fix_player_name(name: str) -> str:
    return sub(r"[^a-zA-Z0-9\- ]+", "", name.strip().title().replace("_", " "))


def parse_event_date(event: Dict):
    start: dtime = isoparse(event["startDate"])
    end: dtime = isoparse(event["endDate"])
    return start + (end - start) / 2


def get_matches() -> List[Tuple[str, int, bool]]:
    # Collect all events.
    url: str = "https://zsr.octane.gg/events"
    page, per_page = 1, 500
    events: List = []
    while True:
        events_content: str = get_content(
            url, params={"page": page, "perPage": per_page, "mode": 3}
        )
        events_json: Dict = parse_json(events_content)
        events += [event for event in events_json["events"] if event_filter(event)]
        print(end=f"\rRequesting Events: {len(events)} Events")
        if events_json["pageSize"] != per_page:
            print("\n")
            break
        page += 1
    events.sort(key=parse_event_date)
    print(*[event["name"] for event in events], sep="\n")
    print()

    # Iterate through events.
    url: str = "https://zsr.octane.gg/matches"
    matches: List = []
    for event_json in tqdm(events, desc="Events"):
        params: Dict = {"event": event_json["_id"]}
        matches_content: str = get_content(url, params=params)
        matches_json: Dict = parse_json(matches_content)
        should_cache: bool = (
            isoparse(event_json["endDate"]).replace(tzinfo=None) < CACHE_TIME
        )
        matches += [(match, should_cache) for match in matches_json["matches"]]
        if should_cache:
            cache(url, matches_content, params=params)

    matches.sort(key=lambda match: isoparse(match[0]["date"]))
    return matches


def update_rankings(
    env: TrueSkill,
    rankings: Dict[str, Rating],
    ratings: List[List[Rating]],
    names: List[List[str]],
    winner: int,
    series: List[int],
    series_total: List[List[List[int]]],
):
    # Update rankings.
    ranks = [1, 1]
    ranks[winner] = 0
    new_ratings = env.rate(ratings, ranks)
    for i in range(2):
        for j, name in enumerate(names[i]):
            rankings[name] = new_ratings[i][j]

    # Update series.
    if len(series_total) <= max(series):
        for s in series_total:
            s.append([0, 0])
        series_total.append([[0, 0] for _ in range(max(series) + 1)])
    series_total[series[winner]][series[not winner]][0] += 1
    series_total[series[winner]][series[not winner]][1] += 1
    series_total[series[not winner]][series[winner]][1] += 1
    series[winner] += 1


def result_gen(match_json, should_cache):
    # Check if we can quickly iterate through games without requesting them.
    if all(
        colour in match_json
        and "players" in match_json[colour]
        and len(match_json[colour]["players"]) == 3
        for colour in ("blue", "orange")
    ):
        for game in match_json["games"]:
            if "duration" in game:
                yield match_json, game["orange"] > game["blue"]
        return

    url: str = f"https://zsr.octane.gg/matches/{match_json['_id']}/games"
    games_content: str = get_content(url)
    if should_cache:
        cache(url, games_content)
    games_json: Dict = parse_json(games_content)

    # Iterate through games.
    for game in games_json["games"]:
        yield game, "winner" in game["orange"]


def setup_ranking(env: TrueSkill, rankings: Dict[str, Rating]) -> List[List[float]]:
    series_total: List[List[List[int]]] = []

    # Iterate through matches.
    for match_json, should_cache in tqdm(get_matches(), desc="Matches"):
        series: List[int] = [0, 0]
        for game_json, winner in result_gen(match_json, should_cache):
            names: List[List[str]] = [[], []]
            ratings: List[List[Rating]] = [[], []]

            for team, colour in enumerate(("blue", "orange")):
                for player in game_json[colour]["players"]:
                    name: str = player["player"]["tag"]
                    name = fix_player_name(name)
                    names[team].append(name)
                    if name not in rankings:
                        rankings[name] = env.create_rating()
                    ratings[team].append(rankings[name])

            if any(len(named) != 3 for named in names):
                break

            update_rankings(env, rankings, ratings, names, winner, series, series_total)

    series_rates: List[List[float]] = [
        [(rate[0] + 1) / (rate[1] + 2) for rate in series] for series in series_total
    ]
    return series_rates
