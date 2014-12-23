import unittest

from minisat import Clause, Solver


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
        s.assignments = {1: None, 2: None, 3: None, 4: None}

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
        s.assignments = {1: None, 2: None, 3: None, 4: None}

        # When
        sol = s.search()

        # Then
        self.assertEqual(sol, {1: True, 2: True, 3: True, 4: True})

if __name__ == '__main__':
    unittest.main()
