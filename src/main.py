from typing import Dict, List, Tuple, Optional

from tabulate import tabulate
from pyperclip import copy as clipboard
from trueskill import Rating, TrueSkill

from kelly import get_best_bet
from player import Player, fix_player_name
from ranking import setup_ranking
from probability import win_probability_best_of


def get_by_name(rankings: Dict[str, Player], name: str):
    name = fix_player_name(name)
    players: List[Player] = [
        player for player in rankings.values() if player.name == name
    ]
    if not players:
        return None
    if len(players) == 1:
        return players[0]
    print(f"Found {len(players)} players named {name}:")
    print(
        *[
            f"#{i + 1} - {name} ({player.region}): {player.slug}"
            for i, player in enumerate(players)
        ],
        sep="\n",
    )
    while True:
        try:
            selected: int = int(input("Select: "))
            return players[selected - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")


def input_players(
    team_names: List[str], rankings: Dict[str, Player], teams: Dict[str, List[Rating]]
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
                player: Optional[Player] = get_by_name(rankings, name)
                if player:
                    ratings[team].append(player.rating)
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
        beta=32.5665, tau=0.47127, draw_probability=0, backend="mpmath"
    )
    rankings: Dict[str, Player] = {}
    setup_ranking(env, rankings)

    print()

    # Print the leaderboard.
    leaderboard: List[Tuple[str, float, float]] = []
    for slug, player in sorted(
        rankings.items(),
        key=lambda slug_player: slug_player[1].rating.mu,
        reverse=True,
    ):
        leaderboard.append(
            (
                player.name,
                player.region,
                player.rating.mu,
                player.rating.sigma,
                player.debut,
            )
        )
    print(tabulate(leaderboard, headers=["Name", "Region", "Mu", "Sigma", "Debut"]))
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
        for best_of in range(3, 8, 2):
            probability: float = win_probability_best_of(env, best_of, *ratings)
            best_bet: float = get_best_bet(probability, ratios)
            output.append(
                ("+" if (probability > 0.5) == (best_bet > 0) else "-")
                + team_names[0 if probability > 0.5 else 1]
                + " in BO"
                + str(best_of)
                + ": "
                + str(round(max(probability, 1 - probability) * 100, 2)).rjust(6)
                + "% ["
                + str(best_of // 2 + 1)
                + "-"
                + next(
                    (
                        str(games)
                        for games in range(best_of // 2)
                        if max(probability, 1 - probability)
                        > 1 - (0.5 + games) / (best_of // 2 + 1.5 + games)
                    ),
                    str(best_of // 2),
                )
                + "] (Bet "
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
