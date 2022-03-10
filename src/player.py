from re import sub
from typing import Dict

from trueskill import Rating, TrueSkill

REGION_RATING: Dict[str, float] = {
    "NA": (94.1040, -15.5676),
    "EU": (100, -15.2423),
    "INT": (97.7606, -15.1796),
    "OCE": (74.2824, -18.2596),
    "SAM": (78.6406, -20.4218),
    "ME": (97.2625, -13.7834),
    "ASIA": (26.6284, -23.6419),
    "AF": (45.8466, -30),  # TODO
}


def fix_player_name(name: str) -> str:
    name = sub(r"[_-]+", " ", name)
    name = name.strip()
    name = sub(r"[^a-zA-Z0-9\- ]+", "", name)
    name = name.title()
    return name


def name_from_slug(slug: str):
    return fix_player_name(slug[slug.index("-") + 1 :])


class Player:
    def __init__(self, slug: str, region: str, env: TrueSkill):
        self.slug: str = slug
        self.name: str = name_from_slug(slug)
        self.region: str = region
        self.rating: Rating = env.create_rating(*REGION_RATING[region])
        self.debut: str = "Unknown"
