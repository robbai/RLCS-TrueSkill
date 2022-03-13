from math import sqrt
from typing import List

from trueskill import Rating, TrueSkill


def win_probability(
    env: TrueSkill, team1: List[Rating], team2: List[Rating], beta_factor: float = 1
) -> float:
    """
    https://github.com/sublee/trueskill/issues/1#issuecomment-149762508
    :return: The probability of "team1" winning a single game
    """
    delta_mu: float = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma: float = sum(r.sigma ** 2 for r in team1 + team2)
    size: int = len(team1) + len(team2)
    denom: float = sqrt(size * env.beta ** 2 * beta_factor + sum_sigma)
    return env.cdf(delta_mu / denom)


def win_probability_best_of(
    env: TrueSkill, best_of: int, team1: List[Rating], team2: List[Rating]
) -> float:
    """
    :return: The probability of "team1" winning the match
    """
    assert best_of % 2 and best_of > 0, best_of
    beta_factor: float = {3: 1.68533, 5: 0.35714, 7: 0.20904}[best_of]
    return win_probability(env, team1, team2, beta_factor)
