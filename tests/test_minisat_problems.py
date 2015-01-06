import unittest

from simplesat.api import Clause, Solver, value


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


def _van_der_waerden_helper(j, n, is_conjugated):
    sign = -1 if is_conjugated else +1
    clauses = []
    max_d = (n - 1) / (j - 1) + 1
    for d in range(1, max_d + 1):
        for i in range(1, n - (j - 1) * d + 1):
            digits = [i + p * d for p in range(0, j)]
            clauses.append(
                Clause([sign*digit for digit in digits]))
    return clauses


# TODO code duplication with examples module
def van_der_waerden(j, k, n):
    clauses = []
    clauses.extend(_van_der_waerden_helper(j, n, False))
    clauses.extend(_van_der_waerden_helper(k, n, True))
    return clauses


class TestMinisatVanDerWaerden(unittest.TestCase):

    def test_van_der_waerden_solvable(self):
        # Given
        j, k, n = 3, 3, 8
        s = Solver()
        clauses = van_der_waerden(j, k, n)

        # TODO Really need to move this to the class...
        vars = {
            abs(lit) for clause in clauses for lit in clause.lits
        }
        s.assignments = {v: None for v in vars}

        for clause in clauses:
            s.add_clause(clause)

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

        # TODO Really need to move this to the class...
        vars = {
            abs(lit) for clause in clauses for lit in clause.lits
        }
        s.assignments = {v: None for v in vars}

        for clause in clauses:
            s.add_clause(clause)

        # When
        solution = s.search()

        # Then
        self.assertFalse(solution)


if __name__ == '__main__':
    unittest.main()
