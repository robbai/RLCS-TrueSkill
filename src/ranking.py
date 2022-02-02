from re import sub
from json import loads as parse_json
from math import log
from typing import Dict, List, Tuple
from datetime import datetime as dtime
from datetime import timedelta

from tqdm import tqdm
from trueskill import Rating, TrueSkill
from dateutil.parser import isoparse
from currency_converter import CurrencyConverter

from requester import cache, get_content
from probability import win_probability_best_of

# Cache events and matches that are older than this.
CACHE_TIME: dtime = dtime.now().replace(tzinfo=None) - timedelta(weeks=1)


cc: CurrencyConverter = CurrencyConverter()

REGION_RATING: Dict[str, float] = {
    "NA": (53.8507, -12.0396),
    "EU": (56.0847, -9.4718),
    "INT": (27.0944, -24.6955),
    "OCE": (27.4025, -23.1297),
    "SAM": (32.2324, -13.8960),
    "ME": (24.1726, -13.2583),
    "ASIA": (19.0171, -18.9193),
    "AF": (9.5971, -10.8331),
}


def event_filter(event: Dict) -> bool:
    if event["region"] == "INT":
        if event["tier"] in ["S", "A", "B"]:
            return True
    if "groups" in event:
        groups: List[str] = event["groups"]
        if "grid" in groups:
            return False
        if "iwo" in groups:
            return True
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
    events = [
        event
        for event in events
        if isoparse(event["startDate"]).replace(tzinfo=None) <= dtime.now()
    ]
    events.sort(key=parse_event_date)

    # Iterate through events.
    matches: List = []
    for event_json in tqdm(events, desc="Events"):
        url: str = f"https://zsr.octane.gg/events/{event_json['slug']}/matches"
        matches_content: str = get_content(url)
        matches_json: Dict = parse_json(matches_content)
        should_cache: bool = (
            isoparse(event_json["endDate"]).replace(tzinfo=None) < CACHE_TIME
        )
        # if not should_cache:
        #     break
        matches += [(match, should_cache) for match in matches_json["matches"]]
        if should_cache:
            cache(url, matches_content)

    matches.sort(key=lambda match: isoparse(match[0]["date"]))
    return matches


def update_rankings(
    env: TrueSkill,
    rankings: Dict[str, Rating],
    ratings: List[List[Rating]],
    names: List[List[str]],
    winner: int,
    result=None,
):
    error = None
    if result:
        probability: float = win_probability_best_of(env, result[0], *ratings)
        error = 1 - probability if result[1] else probability

    # Update rankings.
    ranks = [1, 1]
    ranks[winner] = 0
    new_ratings = env.rate(ratings, ranks)
    for i in range(2):
        for j, name in enumerate(names[i]):
            rankings[name] = new_ratings[i][j]

    return error


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


def setup_ranking(env: TrueSkill, rankings: Dict[str, Rating]):
    arr = []

    # Iterate through matches.
    for match_json, should_cache in tqdm(get_matches(), desc="Matches"):
        result = (
            (match_json["format"]["length"], "winner" in match_json["orange"])
            if "orange" in match_json
            else None
        )
        for i, (game_json, winner) in enumerate(result_gen(match_json, should_cache)):
            if "event" in game_json:
                region: str = game_json["event"]["region"]
            else:
                region: str = game_json["match"]["event"]["region"]

            names: List[List[str]] = [[], []]
            ratings: List[List[Rating]] = [[], []]

            for team, colour in enumerate(("blue", "orange")):
                for player in game_json[colour]["players"]:
                    name: str = player["player"]["tag"]
                    name = fix_player_name(name)
                    names[team].append(name)
                    if name not in rankings:
                        rankings[name] = env.create_rating(*REGION_RATING[region])
                    ratings[team].append(rankings[name])

            if any(len(named) != 3 for named in names):
                break

            error = update_rankings(
                env, rankings, ratings, names, winner, None if i else result
            )
            if error:
                arr.append((match_json["slug"], error))

    print("Upsets:")
    arr.sort(key=lambda a: a[-1])
    print(*arr[:100], sep="\n")
    print("\nExpected:")
    print(*arr[::-1][:100], sep="\n")
