from trueskill import TrueSkill

from ranking import setup_ranking


def main():
    # Setup the ranking.
    env: TrueSkill = TrueSkill(
        sigma=-15.5676, beta=35.1108, tau=0.7317, draw_probability=0, backend="mpmath"
    )
    setup_ranking(env, {})


if __name__ == "__main__":
    main()
