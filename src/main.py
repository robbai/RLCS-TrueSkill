from math import copysign
from typing import Dict, Tuple

from trueskill import TrueSkill

from ranking import games_gen, setup_ranking

TEST: bool = True


def run() -> Dict[int, Tuple[float, int, float]]:
    env: TrueSkill = TrueSkill(
        beta=33.74046, tau=0.46576, draw_probability=0, backend="mpmath"
    )
    return setup_ranking(env)


def main():
    games_gen()
    print()

    if TEST:
        losses: Dict[int, Tuple[float, int, float]] = run()
        print(
            round(
                sum([ld[2] for ld in losses.values()])
                / sum([ld[1] for ld in losses.values()]),
                5,
            )
        )
        return

    from probability import params

    for b, p in {1: 1, 3: 1, 5: 1, 7: 1, 9: 1}.items():
        params[b] = p

    params_delta: Dict[int, float] = {}
    loss_last: Dict[int, float] = {}
    while True:
        losses: Dict[int, Tuple[float, int, float]] = run()
        loss_dir: Dict[int, float] = {
            b: ld[0] / max(1, ld[1]) for b, ld in losses.items()
        }
        print("Dir:", loss_dir)
        params_new: Dict[int, float] = {}
        if loss_last:
            for best_of in params:
                try:
                    params_new[best_of] = params[best_of] + copysign(
                        params_delta[best_of]
                        * loss_dir[best_of]
                        / (loss_dir[best_of] - loss_last[best_of]),
                        loss_dir[best_of],
                    )
                    params_new[best_of] = max(1e-12, params_new[best_of])
                except ZeroDivisionError:
                    params_new[best_of] = params[best_of]
        else:
            for best_of in params:
                params_new[best_of] = 0.5 + (loss_dir[best_of] > 0)
                loss_last[best_of] = 0
        for best_of in params:
            params_delta[best_of] = params_new[best_of] - params[best_of]
            params[best_of] = params_new[best_of]
            loss_last[best_of] = loss_dir[best_of]
        print(
            "Par:", {b: round(p, 5) if p >= 0.000005 else p for b, p in params.items()}
        )
        print()


if __name__ == "__main__":
    main()
