from .minisat import MiniSATSolver  # noqa


def is_satisfiable(rules):
    s = MiniSATSolver(rules)
    return s.search() is not False
