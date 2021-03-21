from json import loads as parse_json
from typing import Dict, List, Tuple

from tqdm import tqdm
from trueskill import Rating, TrueSkill

from requester import get_content

# Archive/Unfinished -> Event -> Match -> Game

unfinished_url: str = "https://api.octane.gg/api/event_list/upcoming"
archive_url: str = "https://api.octane.gg/api/event_list"


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
    return name


def get_matches() -> List[Tuple[str, int, bool]]:
    matches: List[Tuple[str, int, bool]] = []

    for url in (archive_url, unfinished_url):
        unfinished: bool = (url == unfinished_url)

        # Iterate through events.
        main_content: str = get_content(url, can_cache=False)
        event_table: List[Dict] = [
            event for event in parse_json(main_content)["data"] if event_filter(event)
        ]
        print("\n".join(event["Event"] for event in event_table))
        for event in tqdm(
            event_table, desc=("Unfinished" if unfinished else "Archived") + " events"
        ):
            # Add matches.
            matches_url: str = "https://api.octane.gg/api/matches_event/" + event[
                "EventHyphenated"
            ]
            event_content: str = get_content(matches_url, can_cache=not unfinished)
            try:
                match_table: List[Dict] = parse_json(event_content)["data"]
                for match in match_table:
                    games: int = match["Team1Games"] + match["Team2Games"]
                    if games <= 1:
                        continue
                    matches.append((match["match_url"], games, unfinished))
            except Exception:
                pass

    return matches


def setup_ranking(env: TrueSkill, rankings: Dict[str, Rating]):
    matches: List[Tuple[str, int, bool]] = get_matches()

    # Iterate through matches.
    for match_id, games, unfinished in tqdm(matches[::-1], desc="Match list"):
        # for match_id, games in matches[::-1]:
        invalid_match: bool = False

        # Iterate through games (two teams).
        for game_number in range(1, games + 1):
            team_url_format: str = "https://api.octane.gg/api/match_scoreboard_{}/" + match_id + "/" + str(
                game_number
            )

            winner: int = None
            names: List[List[str]] = [[], []]
            ratings: List[List[Rating]] = [[], []]

            for i, team in enumerate(("one", "two")):
                team_url: str = team_url_format.format(team)

                try:
                    team_content: str = get_content(team_url, can_cache=not unfinished)
                    team_table: List[Dict] = parse_json(team_content)["data"]
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
