from typing import Dict, List, Tuple

from tabulate import tabulate
from pyperclip import copy as clipboard
from trueskill import Rating, TrueSkill

from kelly import get_best_bet
from ranking import setup_ranking, fix_player_name
from probability import win_probability_best_of


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
                name: str = input(
                    "Player " + str(index + 1) + " on " + team_names[team] + ": "
                )
                name = fix_player_name(name)
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
    env: TrueSkill = TrueSkill(
        sigma=-15.5676, beta=35.1108, tau=0.7317, draw_probability=0, backend="mpmath"
    )
    rankings: Dict[str, Rating] = {}
    setup_ranking(env, rankings)

    print()

    # Print the leaderboard.
    leaderboard: List[Tuple[str, float, float]] = []
    for player in sorted(
        rankings.items(),
        key=lambda player: player[1].mu,
        reverse=True,
    ):
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
        ratios: Tuple[float, float] = input_ratios(team_names)
        output: List[str] = [
            " " + team_names[0] + " vs " + team_names[1],
            " Return ratios: 1:"
            + str(round(ratios[0], 4))
            + ", 1:"
            + str(round(ratios[1], 4)),
        ]
        for best_of in range(1, 8, 2):
            probability: float = win_probability_best_of(env, best_of, *ratings)
            best_bet: float = get_best_bet(probability, ratios)
            output.append(
                ("+" if (probability > 0.5) == (best_bet > 0) else "-")
                + team_names[0 if probability > 0.5 else 1]
                + " in BO"
                + str(best_of)
                + ": "
                + str(round(max(probability, 1 - probability) * 100, 2)).rjust(6)
                + "% (Bet "
                + str(round(abs(best_bet) * 100, 2)).rjust(6)
                + "% on "
                + team_names[0 if best_bet > 0 else 1].rjust(
                    len(max(team_names, key=len))
                )
                + ")"
            )
        clipboard("```diff\n" + "\n".join(output) + "\n```")
        print()
        print("\n".join(line[1:] for line in output))
        print()


if __name__ == "__main__":
    main()
