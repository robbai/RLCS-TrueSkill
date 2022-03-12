from bayes_opt import BayesianOptimization
from trueskill import TrueSkill
from bayes_opt.util import load_logs
from bayes_opt.event import Events
from bayes_opt.logger import JSONLogger

from ranking import games_gen, setup_ranking


def black_box(beta: float, tau: float) -> float:
    env: TrueSkill = TrueSkill(beta=beta, tau=tau, draw_probability=0, backend="mpmath")
    return 1 / setup_ranking(env)


def main():
    games_gen()
    print()

    # Bounded region of parameter space.
    pbounds = {"beta": (1, 70), "tau": (0.01, 1)}

    optimizer = BayesianOptimization(
        f=black_box,
        pbounds=pbounds,
        random_state=1,
    )

    try:
        load_logs(optimizer, logs=["logs.json"])
    except FileNotFoundError:
        optimizer.probe(
            params={"beta": 33.74046, "tau": 0.46576},
            lazy=True,
        )

    logger = JSONLogger(path="logs.json")
    optimizer.subscribe(Events.OPTIMIZATION_STEP, logger)

    optimizer.maximize(
        init_points=0,
        n_iter=500,
    )

    print(optimizer.max)


if __name__ == "__main__":
    main()
