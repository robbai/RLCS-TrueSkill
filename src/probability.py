from math import exp, sqrt
from typing import Dict, List

from trueskill import Rating, TrueSkill


def win_probability(env: TrueSkill, team1: List[Rating], team2: List[Rating]) -> float:
    """
    https://github.com/sublee/trueskill/issues/1#issuecomment-149762508
    :return: The probability of "team1" winning a single game
    """
    delta_mu: float = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma: float = sum(r.sigma ** 2 for r in team1 + team2)
    size: int = len(team1) + len(team2)
    denom: float = sqrt(size * (env.beta * env.beta) + sum_sigma)
    return env.cdf(delta_mu / denom)


def win_probability_best_of(
    env: TrueSkill, best_of: int, team1: List[Rating], team2: List[Rating]
) -> float:
    """
    :return: The probability of "team1" winning the match
    """
    probability: float = win_probability(env, team1, team2)

    assert best_of % 2, best_of
    if best_of < 3:
        return probability

    m_best_of: Dict[int, float] = {
        3: 12.932017010012988,
        5: 19.374327643101946,
        7: 21.01782242281867,
    }
    best_of = min(best_of, max(m_best_of))

    m: float = m_best_of[best_of]
    return 1 / (1 + exp(m * (0.5 - probability)))
