from math import sqrt
from typing import List, Union
from datetime import datetime as dtime

from trueskill import TrueSkill

from player import Player

MOMENTUM_FACTOR: float = 0.19587
LAN_FACTOR: float = 0.2115


def total_mu(team: List[Player], date: Union[bool, dtime], lan: bool) -> float:
    return sum(
        p.rating.mu
        + p.get_momentum(date) * MOMENTUM_FACTOR
        + p.lan_bonus * LAN_FACTOR * lan
        for p in team
    )


def win_probability(
    env: TrueSkill,
    team1: List[Player],
    team2: List[Player],
    date: Union[bool, dtime],
    lan: bool,
    beta_factor: float = 1,
) -> float:
    """
    https://github.com/sublee/trueskill/issues/1#issuecomment-149762508
    :return: The probability of "team1" winning a single game
    """
    delta_mu: float = total_mu(team1, date, lan) - total_mu(team2, date, lan)
    sum_sigma: float = sum(p.rating.sigma**2 for p in team1 + team2)
    size: int = len(team1) + len(team2)
    denom: float = sqrt(size * env.beta**2 * beta_factor + sum_sigma)
    return env.cdf(delta_mu / denom)


def win_probability_best_of(
    env: TrueSkill,
    best_of: int,
    team1: List[Player],
    team2: List[Player],
    date: Union[bool, dtime],
    lan: bool,
) -> float:
    """
    :return: The probability of "team1" winning the match
    """
    assert best_of % 2 and best_of > 0, best_of
    beta_factor: float = {3: 1.42774, 5: 0.34486, 7: 0.19642}[best_of]
    return win_probability(env, team1, team2, date, lan, beta_factor)
