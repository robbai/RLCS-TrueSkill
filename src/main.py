import math
import itertools
from typing import Dict, List, Tuple

from tabulate import tabulate
from pyperclip import copy as clipboard
from trueskill import Rating, TrueSkill

from kelly import get_best_bet
from ranking import setup_ranking


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


def input_players(
    team_names: List[str], rankings: Dict[str, Rating], teams: Dict[str, List[Rating]]
):
    ratings: List[List[Rating]] = [[], []]
    for team in range(2):
        if team_names[team] in teams:
            ratings[team] = teams[team_names[team]]
            continue
        for index in range(3):
            while True:
                name = input(
                    "Player " + str(index + 1) + " on " + team_names[team] + ": "
                ).title()
                if name in rankings:
                    ratings[team].append(rankings[name])
                    break
                else:
                    print("Couldn't find player")
        teams[team_names[team]] = ratings[team]
    return ratings


def input_ratios(teams: List[str]) -> Tuple[float, float]:
    ratio1: float = float(input(teams[0] + " return ratio: "))
    ratio2: float = float(input(teams[1] + " return ratio: "))
    inaccuracy: float = (ratio1 * -ratio2 + ratio1 + ratio2) / (ratio1 - 1)
    ratio1 = (2 * ratio2 + inaccuracy) / (2 * ratio2 + inaccuracy - 2)
    ratio2 += inaccuracy / 2
    return ratio1, ratio2


def main():
    # Setup the ranking.
    env: TrueSkill = TrueSkill(draw_probability=0, backend="mpmath")
    rankings: Dict[str, Rating] = {}
    setup_ranking(env, rankings)

    # Print the leaderboard.
    leaderboard: List[Tuple[str, float, float]] = []
    for player in sorted(
        rankings.items(), key=lambda player: env.expose(player[1]), reverse=True,
    ):
        if player[1].sigma > 3:
            continue
        leaderboard.append((player[0], player[1].mu, player[1].sigma))
    print(tabulate(leaderboard, headers=["Name", "Mu", "Sigma"]))
    print()

    # Dictionary of team names to rankings.
    teams: Dict[str, List[Rating]] = {}

    # Input loop
    while True:
        team_names: List[str] = [
            input("Team " + str(i + 1) + ": ").upper() for i in range(2)
        ]
        ratings: List[List[Rating]] = input_players(team_names, rankings, teams)
        probability: float = win_probability(env, *ratings)
        ratios: Tuple[float, float] = input_ratios(team_names)
        output: List[str] = [
            team_names[0] + " vs " + team_names[1],
            "Return ratios: 1:"
            + str(round(ratios[0], 4))
            + ", 1:"
            + str(round(ratios[1], 4)),
        ]
        for best_of in range(1, 8, 2):
            probability_best_of: float = win_probability_best_of(best_of, probability)
            best_bet: float = get_best_bet(probability_best_of, ratios)
            output.append(
                team_names[0 if probability_best_of > 0.5 else 1]
                + " in BO"
                + str(best_of)
                + ": "
                + str(
                    round(max(probability_best_of, 1 - probability_best_of) * 100, 2)
                ).rjust(6)
                + "% (Bet "
                + str(round(abs(best_bet) * 100, 2)).rjust(6)
                + "% on "
                + team_names[0 if best_bet > 0 else 1].rjust(
                    len(max(team_names, key=len))
                )
                + ")"
            )
        clipboard("```\n" + "\n".join(output) + "\n```")
        print()
        print("\n".join(output))
        print()


if __name__ == "__main__":
    main()
