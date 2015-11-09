from .minisat import MiniSATSolver, SatisifiabilityError  # noqa


def is_satisfiable(rules):
    s = MiniSATSolver(rules)
    try:
        s.search()
        return True
    except SatisifiabilityError:
        return False
