from math import sqrt
from typing import List, Union
from datetime import datetime as dtime

from trueskill import TrueSkill

from player import Player

MOMENTUM_FACTOR: float = 0.19587


def total_mu(team: List[Player], date: Union[bool, dtime]) -> float:
    return sum(p.rating.mu + p.get_momentum(date) * MOMENTUM_FACTOR for p in team)


def win_probability(
    env: TrueSkill,
    team1: List[Player],
    team2: List[Player],
    date: Union[bool, dtime],
    beta_factor: float = 1,
) -> float:
    """
    https://github.com/sublee/trueskill/issues/1#issuecomment-149762508
    :return: The probability of "team1" winning a single game
    """
    delta_mu: float = total_mu(team1, date) - total_mu(team2, date)
    sum_sigma: float = sum(p.rating.sigma ** 2 for p in team1 + team2)
    size: int = len(team1) + len(team2)
    denom: float = sqrt(size * env.beta ** 2 * beta_factor + sum_sigma)
    return env.cdf(delta_mu / denom)


def win_probability_best_of(
    env: TrueSkill,
    best_of: int,
    team1: List[Player],
    team2: List[Player],
    date: Union[bool, dtime],
) -> float:
    """
    :return: The probability of "team1" winning the match
    """
    assert best_of % 2 and best_of > 0, best_of
    beta_factor: float = {3: 1.75794, 5: 0.37771, 7: 0.20026}[best_of]
    return win_probability(env, team1, team2, date, beta_factor)
