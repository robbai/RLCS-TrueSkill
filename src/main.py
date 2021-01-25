from json import loads as parse_json
from time import time
from typing import Dict, List, Tuple

from tqdm import tqdm
from tabulate import tabulate
from trueskill import Rating, TrueSkill

from requester import get_content

# Main -> Event -> Match -> Game

url: str = "https://api.octane.gg/api/event_list"


def event_filter(event: Dict) -> bool:
    return (event["type"] == "RLCS" or "RLCS" in event["Event"]) and (
        "North America" in event["Event"]
        or "Europe" in event["Event"]
        or "World Championship" in event["Event"]
    )


if __name__ == "__main__":
    time_started: float = time()
    mu_env: float = 2700
    sigma_env: float = mu_env / 4.5
    env: TrueSkill = TrueSkill(mu=mu_env, sigma=sigma_env)
    rankings: Dict[str, Rating] = {}

    # Iterate through events.
    main_content: str = get_content(url)
    event_table: List[Dict] = [
        event for event in parse_json(main_content)["data"] if event_filter(event)
    ]
    for event in event_table:
        print(event["Event"])

        # Iterate through matches.
        matches_url: str = "https://api.octane.gg/api/matches_event/" + event[
            "EventHyphenated"
        ]
        event_content: str = get_content(matches_url)
        match_table: List[Dict] = parse_json(event_content)["data"]
        for match in tqdm(match_table):
            invalid_match: bool = False
            games: int = match["Team1Games"] + match["Team2Games"]
            if games <= 1:
                continue

            # Iterate through games (two teams).
            for game_number in range(1, games + 1):
                team_url_format: str = "https://api.octane.gg/api/match_scoreboard_{}/" + match[
                    "match_url"
                ] + "/" + str(
                    game_number
                )

                winner: int = None
                names: List[List[str]] = [[], []]
                ratings: List[List[Rating]] = [[], []]

                for i, team in enumerate(("one", "two")):
                    team_url: str = team_url_format.format(team)

                    try:
                        team_content: str = get_content(team_url)
                        team_table: List[Dict] = parse_json(team_content)["data"]
                        winner = team_table[0]["Winner"]
                        for name in team_table[:-1]:  # Last "player" is the sum.
                            names[i].append(name["Player"].title())
                            if not names[i][-1] in rankings:
                                rankings[names[i][-1]] = env.create_rating()
                            ratings[i].append(rankings[names[i][-1]])
                    except Exception:
                        invalid_match = True
                        break

                if invalid_match:
                    break

                ranks = [1, 1]
                ranks[winner] = 0
                new_ratings = env.rate(ratings, ranks)
                for i in range(2):
                    for j, name in enumerate(names[i]):
                        rankings[name] = new_ratings[i][j]

                if time() - time_started > 600:
                    leaderboard: List[Tuple[str, float, float]] = []
                    for player in sorted(
                        rankings.items(),
                        key=lambda player: env.expose(player[1]),
                        reverse=True,
                    ):
                        # if player[1].sigma > sigma_env / 2: continue
                        leaderboard.append(
                            (player[0], str(player[1].mu), str(player[1].sigma))
                        )
                    print(tabulate(leaderboard, headers=["Name", "Mu", "Sigma"]))
                    exit()
