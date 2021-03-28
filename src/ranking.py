from json import loads as parse_json
from typing import Dict, List, Tuple, Optional
from datetime import datetime as dtime
from datetime import timedelta

from tqdm import tqdm
from trueskill import Rating, TrueSkill

from requester import cache, get_content, remove_cache

# Archive/Unfinished -> Event -> Match -> Game

unfinished_url: str = "https://api.octane.gg/api/event_list/upcoming"
archive_url: str = "https://api.octane.gg/api/event_list"

# Cache events and invalid matches that are older than this.
# All valid matches are cached.
CACHE_TIME: dtime = dtime.now() - timedelta(days=90)


def event_filter(event: Dict) -> bool:
    name: str = event["Event"]
    type: str = event["type"]
    if not (
        name.startswith("RLCS")
        or name.startswith("RLRS")
        or type == "RLCS"
        or type == "RLRS"
    ):
        return False
    if "Qualifier" in name:
        return True
    prize: str = event["prize"]
    return prize and prize[0] == "$" and float(prize[1:].replace(",", "")) >= 25000


def fix_player_name(name: str) -> str:
    if name == "Scrub":
        name = "Scrub Killa"

    # https://octane.gg/match/8810136
    if name == "M":
        name = "Saizen"
    if name == "Radosin":
        name = "Radosin75"
    if name == "Joyo!":
        name = "Joyo"

    return name


def parse_date(data: Dict) -> dtime:
    return dtime.strptime(data["Date"].split("T", 1)[0], "%Y-%m-%d")


def get_matches() -> List[Tuple[str, int, bool]]:
    matches: List[Tuple[str, int, bool]] = []

    for url in (unfinished_url, archive_url):
        unfinished: bool = (url == unfinished_url)

        # Iterate through events.
        main_content: str = get_content(url)
        event_table: List[Dict] = [
            event for event in parse_json(main_content)["data"] if event_filter(event)
        ]
        event_results: List[str] = []
        for event in tqdm(
            event_table, desc=("Unfinished" if unfinished else "Archived") + " events"
        ):
            # Add matches.
            matches_url: str = "https://api.octane.gg/api/matches_event/" + event[
                "EventHyphenated"
            ]
            event_content: str = get_content(matches_url)
            event_matches: List[Tuple[str, int, bool]] = []
            try:
                match_table: List[Dict] = parse_json(event_content)["data"]
                if parse_date(match_table[0]) < CACHE_TIME:
                    cache(matches_url, event_content)
                for match in match_table:
                    games: int = match["Team1Games"] + match["Team2Games"]
                    if games <= 1:
                        continue
                    event_matches.append((match["match_url"], games, unfinished))
            except Exception:
                continue
            if event_matches:
                matches += event_matches
                event_results.append(
                    event["Event"] + " (" + str(len(event_matches)) + ")"
                )
        print("\n".join(event_results))

    return matches


def setup_ranking(env: TrueSkill, rankings: Dict[str, Rating]):
    matches: List[Tuple[str, int, bool]] = get_matches()

    # Iterate through matches.
    for match_id, games, unfinished in tqdm(matches[::-1], desc="Match list"):
        invalid_match: bool = False

        # Iterate through games.
        for game_number in range(1, games + 1):
            team_url_format: str = "https://api.octane.gg/api/match_scoreboard_{}/" + match_id + "/" + str(
                game_number
            )

            winner: int = None
            names: List[List[str]] = [[], []]
            ratings: List[List[Rating]] = [[], []]

            # Iterate through the two teams.
            for i, team in enumerate(("one", "two")):
                team_url: str = team_url_format.format(team)

                team_date: Optional[dtime] = None
                try:
                    team_content: str = get_content(team_url)
                    team_table: List[Dict] = parse_json(team_content)["data"]
                    cache(team_url, team_content)
                    team_date = parse_date(team_table[0])
                    winner = i if team_table[0]["Winner"] else not i
                    for name in team_table[:-1]:  # Last "player" is the sum.
                        title_name: str = name["Player"].title().strip()
                        title_name = fix_player_name(title_name)
                        names[i].append(title_name)
                        if title_name not in rankings:
                            rankings[title_name] = env.create_rating()
                        ratings[i].append(rankings[title_name])
                except Exception:
                    invalid_match = True
                    if not team_date or team_date >= CACHE_TIME:
                        remove_cache(team_url)
                    break

            if invalid_match or any(len(named) != 3 for named in names):
                break

            ranks = [1, 1]
            ranks[winner] = 0
            new_ratings = env.rate(ratings, ranks)
            for i in range(2):
                for j, name in enumerate(names[i]):
                    rankings[name] = new_ratings[i][j]
    print()
