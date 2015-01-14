import unittest

from simplesat.api import Clause, Solver, value
from simplesat.examples.van_der_waerden import van_der_waerden


class TestMinisatProblems(unittest.TestCase):
    """Run the Minisat solver on a range of test problems.
    """
    def test_no_assumptions(self):
        # A simple problem with only unit propagation, no assumptions (except
        # for the initial one), no backtracking, and no conflicts.

        # Given
        s = Solver()
        cl1 = Clause([1, -2])
        cl2 = Clause([1,  2, -3])
        cl3 = Clause([1,  2,  3, -4])
        s.add_clause(cl1)
        s.add_clause(cl2)
        s.add_clause(cl3)
        s._setup_assignments()

        # When
        sol = s.search()

        # Then
        self.assertEqual(sol, {1: True, 2: True, 3: True, 4: True})

    def test_one_assumption(self):
        # A simple problem with only unit propagation, where one additional
        # assumption needs to be made.

        # Given
        s = Solver()
        cl1 = Clause([1, -2])
        cl3 = Clause([-1,  -2,  3, -4])
        s.add_clause(cl1)
        s.add_clause(cl3)
        s._setup_assignments()

        # When
        sol = s.search()

        # Then
        self.assertEqual(sol, {1: True, 2: True, 3: True, 4: True})


def check_solution(clauses, solution):
    for clause in clauses:
        for lit in clause:
            if value(lit, solution):
                # Clause is satisfied.
                break
        else:
            # No true literal
            return False
    return True


class TestMinisatVanDerWaerden(unittest.TestCase):

    def test_van_der_waerden_solvable(self):
        # Given
        j, k, n = 3, 3, 8
        s = Solver()
        clauses = van_der_waerden(j, k, n)
        for clause in clauses:
            s.add_clause(clause)
        s._setup_assignments()

        # When
        solution = s.search()

        # Then
        self.assertTrue(check_solution(s.clauses, solution),
                        msg='{} does not satisfy SAT problem'.format(solution))

    def test_van_der_waerden_not_solvable(self):
        # Given
        j, k, n = 3, 3, 9
        s = Solver()
        clauses = van_der_waerden(j, k, n)
        for clause in clauses:
            s.add_clause(clause)
        s._setup_assignments()

        # When
        solution = s.search()

        # Then
        self.assertFalse(solution)
