from json import loads as parse_json
from typing import Dict, List, Tuple
from datetime import datetime as dtime
from datetime import timedelta

from tqdm import tqdm
from trueskill import Rating, TrueSkill
from dateutil.parser import isoparse
from currency_converter import CurrencyConverter

from player import Player
from requester import cache, get_content

# Cache events and matches that are older than this.
CACHE_TIME: dtime = dtime.now().replace(tzinfo=None) - timedelta(weeks=1)


cc: CurrencyConverter = CurrencyConverter()


def event_filter(event: Dict) -> bool:
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
    print(*[event["name"] for event in events], sep="\n")
    print()

    # Iterate through events.
    matches: List = []
    for event_json in tqdm(events, desc="Events"):
        url: str = f"https://zsr.octane.gg/events/{event_json['slug']}/matches"
        matches_content: str = get_content(url)
        matches_json: Dict = parse_json(matches_content)
        should_cache: bool = (
            isoparse(event_json["endDate"]).replace(tzinfo=None) < CACHE_TIME
        )
        matches += [(match, should_cache) for match in matches_json["matches"]]
        if should_cache:
            cache(url, matches_content)

    matches.sort(key=lambda match: isoparse(match[0]["date"]))
    return matches


def update_rankings(
    env: TrueSkill,
    rankings: Dict[str, Player],
    slugs: List[List[str]],
    winner: int,
    date: dtime = None,
):
    ranks = [1, 1]
    ranks[winner] = 0
    ratings: List[List[Rating]] = [
        [rankings[slug].rating for slug in roster] for roster in slugs
    ]
    new_ratings = env.rate(ratings, ranks)
    for i in range(2):
        for j, slug in enumerate(slugs[i]):
            rankings[slug].update(new_ratings[i][j], date)


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


def setup_ranking(env: TrueSkill, rankings: Dict[str, Player]):
    # Iterate through matches.
    for match_json, should_cache in tqdm(get_matches(), desc="Matches"):
        for game_json, winner in result_gen(match_json, should_cache):
            if "event" in game_json:
                region: str = game_json["event"]["region"]
            else:
                region: str = game_json["match"]["event"]["region"]

            slugs: List[List[str]] = [[], []]

            for team, colour in enumerate(("blue", "orange")):
                for player in game_json[colour]["players"]:
                    slug: str = player["player"]["slug"]
                    slugs[team].append(slug)
                    if slug not in rankings:
                        player: Player = Player(slug, region, env)
                        player.debut = (
                            game_json["event"]["name"]
                            if "event" in game_json
                            else game_json["match"]["event"]["name"]
                        )
                        rankings[slug] = player

            if any(len(roster) != 3 for roster in slugs):
                break

            date: dtime = isoparse(game_json["date"])
            update_rankings(env, rankings, slugs, winner, date)
