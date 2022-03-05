from typing import Dict

from trueskill import Rating, TrueSkill

REGION_RATING: Dict[str, float] = {
    "NA": (91.8828, -12.0396),
    "EU": (108.2387, -9.4718),
    "INT": (64.6425, -24.6955),
    "OCE": (79.8350, -23.1297),
    "SAM": (84.2898, -13.8960),
    "ME": (81.3772, -13.2583),
    "ASIA": (13.0664, -18.9193),
    "AF": (5.1691, -10.8331),
}


class Player:
    def __init__(self, name: str, region: str, env: TrueSkill):
        self.name: str = name
        self.region: str = region
        self.rating: Rating = env.create_rating(*REGION_RATING[region])
        self.debut: str = "Unknown"
