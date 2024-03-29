from re import sub
from typing import Dict, Union, Optional
from datetime import datetime as dtime

from trueskill import Rating, TrueSkill

LAN_SCALE: float = 0.1300


REGION_RATING: Dict[str, float] = {
    "NA": (98.33, -12.58),
    "EU": (100, -14.58),
    "INT": (98.9, -16.09),
    "OCE": (73.52, -17.5),
    "SAM": (80.23, -19.8),
    "ME": (71.2, -21.48),
    "ASIA": (28.12, -29.24),
    "AF": (19.08, -25.85),
}


DEDUPED_SLUGS: Dict[str, str] = {
    "41d5-radosin75": "41d5-radosin",
    "23f9-spectre": "23f9-simas",
    "9a22-scrubbed": "9a22-scrub",
    "456e-stepsisterrrr": "9a22-scrub",
    "433d-sadness": "433d-sad",
    "e7f1-losttssj": "e7f1-lostt",
    "a133-sweaty_clarence": "a133-sweaty",
}


def dedupe_slug(slug: str) -> str:
    return DEDUPED_SLUGS[slug] if slug in DEDUPED_SLUGS else slug


def fix_player_name(name: str) -> str:
    name = sub(r"[_-]+", " ", name)
    name = name.strip()
    name = sub(r"[^a-zA-Z0-9\- ]+", "", name)
    name = name.title()
    return name


def name_from_slug(slug: str):
    return fix_player_name(slug[slug.index("-") + 1 :])


def different_date(d1: Optional[dtime], d2: Optional[dtime]):
    if (not d1) != (not d2):
        return True
    return d1.day != d2.day or d1.month != d2.month or d1.year != d2.year


class Player:
    def __init__(self, slug: str, region: str, env: TrueSkill):
        self.slug: str = slug
        self.name: str = name_from_slug(slug)
        self.region: str = region
        self.rating: Rating = env.create_rating(*REGION_RATING[region])
        self.debut: str = "Unknown"
        self.last_played: Optional[dtime] = None
        self.momentum: float = 0  # Total mu change today.
        self.lan_bonus: float = 0

    def update(self, rating: Rating, date: Optional[dtime] = None, lan: bool = False):
        if different_date(self.last_played, date):
            self.reset(date)
        delta_rating: float = rating.mu - self.rating.mu
        self.momentum += delta_rating
        self.lan_bonus += delta_rating * LAN_SCALE * lan
        self.rating = rating

    def reset(self, date: Optional[dtime] = None):
        self.last_played = date
        self.momentum = 0

    def get_momentum(self, date: Union[bool, dtime]):
        if isinstance(date, bool):
            return self.momentum * date
        return 0 if different_date(self.last_played, date) else self.momentum
