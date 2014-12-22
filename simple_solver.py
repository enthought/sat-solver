"""A simple SAT solver using a dictionary of watched literals.

This implementation is based very heavily on
http://sahandsaba.com/understanding-sat-by-implementing-a-simple-sat-solver-in-python.html

"""

from collections import defaultdict

from utils import Literal


class Watchlist(object):

    def __init__(self, clauses=None):
        self._watchlist = defaultdict(list)
        if clauses is None:
            clauses = []
        for clause in clauses:
            self.add_clause(clause)

    def add_clause(self, clause):
        self._watchlist[clause[0]].append(clause)

    def update(self, false_literal,  assignments):
        # Note: this can run indefinitely if updating with a false_literal
        # which does not correspond to a False variable in assignments. The
        # following assert checks for this inconsistency.
        assert assignments[false_literal.name] is false_literal.is_conjugated

        clauses = self._watchlist[false_literal]
        while len(clauses) > 0:
            clause = clauses[-1]
            for literal in clause:
                var = literal.name
                if assignments[var] is None or \
                        assignments[var] is not literal.is_conjugated:
                    # Found an alternative literal; migrate clause.
                    self._watchlist[literal].append(clause)
                    clauses.pop()
                    break
            else:
                # No alternative was found.
                return False

        # All clauses have been re-assigned.
        return True

    def dump(self):
        for key, values in self._watchlist.items():
            print key, ':'
            for clause in values:
                print '\t', clause


class SimpleSATSolver(object):

    def __init__(self, clauses):
        self._clauses = clauses
        self.variables = list({
            lit.name for clause in clauses for lit in clause
        })

    def _setup(self):
        # Boolean assignment that the solver is currently trying.
        self._assignment = {variable: None for variable in self.variables}

        # State of the solver. Each value is a list which will contain the
        # boolean variables that have been tried for the corresponding
        # variable.
        self._state = {variable: [] for variable in self.variables}

        # Watchlist on the given clauses.
        self._watchlist = Watchlist(self._clauses)

    def solve(self):
        """Return an iterator over all solutions for this SAT problem.
        """
        self._setup()

        index = 0
        while True:
            if index == len(self.variables):
                yield self._assignment.copy()
                index -= 1
                continue

            tried_something = False
            variable = self.variables[index]
            for choice in [True, False]:
                if choice in self._state[variable]:
                    # We've already tried this.
                    continue

                self._state[variable].append(choice)
                self._assignment[variable] = choice
                tried_something = True

                succeeded = self._watchlist.update(
                    Literal(variable, is_conjugated=choice),
                    self._assignment)
                if not succeeded:
                    self._assignment[variable] = None
                else:
                    index += 1
                    break

            if not tried_something:
                if index == 0:
                    return
                else:
                    # Backtrack.
                    self._state[variable] = []
                    self._assignment[variable] = None
                    index -= 1
