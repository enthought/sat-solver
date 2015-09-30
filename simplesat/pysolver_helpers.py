from simplesat.sat import MiniSATSolver


def solver_from_rules_set(rules, policy=None):
    """
    Construct a SAT solver from a rules generator.

    Parameters
    ----------
    pool: Pool
    rules: RulesGenerator

    Returns
    -------
    solver: Solver.

    """
    s = MiniSATSolver(policy)
    for rule in rules:
        s.add_clause(rule.literals)
    s._setup_assignments()
    return s


def is_satisfiable(rules):
    s = solver_from_rules_set(rules)
    return s.search() is not False
