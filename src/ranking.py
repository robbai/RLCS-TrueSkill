from copy import deepcopy
from json import loads as parse_json
from typing import Dict, List, Tuple, Optional
from datetime import datetime as dtime
from datetime import timedelta

from tqdm import tqdm
from trueskill import Rating, TrueSkill
from dateutil.parser import isoparse
from currency_converter import CurrencyConverter

from player import REGION_RATING, Player, dedupe_slug, get_by_name, fix_player_name
from requester import cache, get_content

# Cache events and matches that are older than this.
CACHE_TIME: dtime = dtime.now().replace(tzinfo=None) - timedelta(weeks=1)

TODAY: dtime = dtime.now().replace(hour=0, minute=0, second=0, microsecond=0)


cc: CurrencyConverter = CurrencyConverter()


PRE_MANUAL: Optional[Dict[str, Rating]] = None


def event_filter(event: Dict) -> bool:
    if event["name"] in ["Gamers Without Borders 2022", "Gamers8 2022"]:
        return False
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
        matches += [
            (match, should_cache)
            for match in matches_json["matches"]
            if isoparse(match["date"]).replace(tzinfo=None) < TODAY
        ]
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
    lan: bool = False,
):
    ranks = [1, 1]
    ranks[winner] = 0
    ratings: List[List[Rating]] = [
        [rankings[slug].rating for slug in roster] for roster in slugs
    ]
    new_ratings = env.rate(ratings, ranks)
    for i in range(2):
        for j, slug in enumerate(slugs[i]):
            rankings[slug].update(new_ratings[i][j], date, lan)


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


def add_manual_matches(env: TrueSkill, rankings: Dict[str, Player]):
    manual_games: int = 0
    teams: Dict[str, List[str]] = {}
    try:
        input("Manual matches:")
    except KeyboardInterrupt:
        exit()
    named: Dict[str, Player] = {}
    for line in open("manual.txt", "r").readlines():
        line: str = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens: List[str] = line.split(" ")
        if tokens[0].isnumeric() and str(int(tokens[0])) == tokens[0]:
            # Games.
            teams_playing: List[str] = [team.upper() for team in tokens[1:]]
            for _ in range(int(tokens[0])):
                players: List[List[Player]] = [teams[team] for team in teams_playing]
                assert all(len(n) == 3 for n in players)
                print(
                    ", ".join(p.name for p in players[0])
                    + " beat "
                    + ", ".join(p.name for p in players[1])
                )
                update_rankings(
                    env,
                    rankings,
                    [[p.slug for p in t] for t in players],
                    0,
                )
                manual_games += 1
        elif len(tokens) > 1:
            # New player.
            team_name: str = tokens[0].upper()
            player_name: str = fix_player_name(" ".join(tokens[1:]))
            if team_name not in teams:
                teams[team_name] = []
            player: Player = (
                named[player_name]
                if player_name in named
                else get_by_name(rankings, player_name)
            )
            if not player:
                region: str = None
                while region not in REGION_RATING:
                    region = input(f"Region for {player_name}: ").upper()
                player = Player(f"????-{player_name.lower()}", region, env)
                rankings[player.slug] = player
            named[player_name] = player
            teams[team_name].append(player)
            teams[team_name].sort(key=lambda player: player.name)
        elif tokens[0] == "res":
            count: int = 0
            for player in rankings.values():
                if not player.last_played:
                    player.reset()
                    count += 1
            print(f"End of day, reset {count} players")
        else:
            print("Unrecognised line: '" + line + "'")
            assert False, line
    print("Manual matches: " + str(manual_games) + " games")


def setup_ranking(env: TrueSkill) -> Dict[str, Rating]:
    rankings: Dict[str, Rating] = {}

    global PRE_MANUAL
    if not PRE_MANUAL:
        # Iterate through matches.
        for match_json, should_cache in tqdm(get_matches(), desc="Matches"):
            date: dtime = isoparse(match_json["date"])
            for game_json, winner in result_gen(match_json, should_cache):
                if "event" in game_json:
                    region: str = game_json["event"]["region"]
                else:
                    region: str = game_json["match"]["event"]["region"]
                lan: bool = region == "INT"

                slugs: List[List[str]] = [[], []]

                for team, colour in enumerate(("blue", "orange")):
                    for player in game_json[colour]["players"]:
                        slug: str = dedupe_slug(player["player"]["slug"])
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

                update_rankings(env, rankings, slugs, winner, date, lan)
        PRE_MANUAL = deepcopy(rankings)
    else:
        rankings = deepcopy(PRE_MANUAL)

    # Manual matches.
    add_manual_matches(env, rankings)

    return rankings
