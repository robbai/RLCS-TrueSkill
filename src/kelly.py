from typing import Tuple


def calculate_fraction(probability: float, ratio: float):
    return (probability * ratio - 1) / (ratio - 1)


def get_best_bet(probability: float, ratios: Tuple[float, float]) -> float:
    fraction1 = calculate_fraction(probability, ratios[0])
    fraction2 = calculate_fraction(1 - probability, ratios[1])
    return max(0, fraction1) if fraction1 > fraction2 else -max(0, fraction2)
