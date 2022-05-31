from re import sub
from typing import Dict, Union, Optional
from datetime import datetime as dtime

from trueskill import Rating, TrueSkill

REGION_RATING: Dict[str, float] = {
    "NA": (97.26, -15.5676),
    "EU": (100, -15.2423),
    "INT": (99.82, -15.1796),
    "OCE": (75.69, -18.2596),
    "SAM": (76.64, -20.4218),
    "ME": (77.45, -13.7834),
    "ASIA": (46.63, -23.6419),
    "AF": (35.87, -30),  # TODO
}


DEDUPED_SLUGS: Dict[str, str] = {
    "41d5-radosin75": "41d5-radosin",
    "23f9-spectre": "23f9-simas",
    "9a22-scrubbed": "9a22-scrub",
    "456e-stepsisterrrr": "9a22-scrub",
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

    def update(self, rating: Rating, date: Optional[dtime] = None):
        if different_date(self.last_played, date):
            self.reset(date)
        self.momentum += rating.mu - self.rating.mu
        self.rating = rating

    def reset(self, date: Optional[dtime] = None):
        self.last_played = date
        self.momentum = 0

    def get_momentum(self, date: Union[bool, dtime]):
        if isinstance(date, bool):
            return self.momentum * date
        return 0 if different_date(self.last_played, date) else self.momentum
