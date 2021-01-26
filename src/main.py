import math
import itertools
from json import loads as parse_json
from typing import Dict, List, Tuple

from tqdm import tqdm
from tabulate import tabulate
from trueskill import Rating, TrueSkill

from requester import get_content

# Main -> Event -> Match -> Game

url: str = "https://api.octane.gg/api/event_list"


# https://github.com/sublee/trueskill/issues/1#issuecomment-149762508
def win_probability(env: TrueSkill, team1: List[Rating], team2: List[Rating]) -> float:
    delta_mu: float = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma: float = sum(r.sigma ** 2 for r in itertools.chain(team1, team2))
    size: int = len(team1) + len(team2)
    denom: float = math.sqrt(size * (env.beta * env.beta) + sum_sigma)
    return env.cdf(delta_mu / denom)


def win_probability_best_of(
    best_of: int, probability: float, score: Tuple[int, int] = (0, 0)
) -> float:
    first_to: int = best_of // 2 + 1
    if score[0] == first_to:
        return 1
    elif score[1] == first_to:
        return 0
    return probability * win_probability_best_of(
        best_of, probability, (score[0] + 1, score[1])
    ) + (1 - probability) * win_probability_best_of(
        best_of, probability, (score[0], score[1] + 1)
    )


def event_filter(event: Dict) -> bool:
    # return (event["type"] == "RLCS" or "RLCS" in event["Event"]
    #         # or "RLRS" in event["Event"]
    #         ) and (
    #     "North America" in event["Event"]
    #     or "Europe" in event["Event"]
    #     or "World Championship" in event["Event"]
    # )
    prize: str = event["prize"]
    return prize and prize[0] == "$" and float(prize[1:].replace(",", "")) >= 25000


def main():
    env: TrueSkill = TrueSkill(draw_probability=0, backend="mpmath")
    rankings: Dict[str, Rating] = {}

    matches: List[Tuple[str, int]] = []

    # Iterate through events.
    main_content: str = get_content(url)
    event_table: List[Dict] = [
        event for event in parse_json(main_content)["data"] if event_filter(event)
    ]
    for event in tqdm(event_table, desc="Event table"):

        # Add matches.
        matches_url: str = "https://api.octane.gg/api/matches_event/" + event[
            "EventHyphenated"
        ]
        event_content: str = get_content(matches_url)
        match_table: List[Dict] = parse_json(event_content)["data"]
        for match in match_table:
            games: int = match["Team1Games"] + match["Team2Games"]
            if games <= 1:
                continue
            matches.append((match["match_url"], games))

    # Iterate through matches.
    for match_id, games in tqdm(matches[::-1], desc="Match list"):
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

            if invalid_match or not all(len(named) == 3 for named in names):
                break

            ranks = [1, 1]
            ranks[winner] = 0
            new_ratings = env.rate(ratings, ranks)
            for i in range(2):
                for j, name in enumerate(names[i]):
                    rankings[name] = new_ratings[i][j]
    print()

    # Print the leaderboard.
    leaderboard: List[Tuple[str, float, float]] = []
    for player in sorted(
        rankings.items(), key=lambda player: env.expose(player[1]), reverse=True,
    ):
        if player[1].sigma > 3:
            continue
        leaderboard.append((player[0], str(player[1].mu), str(player[1].sigma)))
    print(tabulate(leaderboard, headers=["Name", "Mu", "Sigma"]))
    print()

    # Input loop
    while True:
        ratings: List[List[Rating]] = [[], []]
        for i in range(6):
            while True:
                index: int = i % 3
                team: int = i // 3
                name = input(
                    "Player " + str(index + 1) + " on team " + str(team + 1) + ": "
                ).title()
                if name in rankings:
                    ratings[team].append(rankings[name])
                    break
                else:
                    print("Couldn't find player")
        probability: float = win_probability(env, *ratings)
        print("Win probabilities:")
        for best_of in range(1, 8, 2):
            print(
                "Team 1 in BO"
                + str(best_of)
                + ": "
                + str(round(win_probability_best_of(best_of, probability) * 100, 2))
                + "%"
            )
        print()


if __name__ == "__main__":
    main()
