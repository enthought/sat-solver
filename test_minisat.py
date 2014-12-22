import unittest

import mock

from minisat import Clause, Solver


class TestClause(unittest.TestCase):

    def test_propagate(self):
        # Given
        c = Clause([1, -2, 5])
        assignments = {1: False, 2: None, 5: None}

        # When
        unit = c.propagate(assignments, -1)

        # Then
        self.assertIsNone(unit)
        self.assertItemsEqual(c.lits, [5, -2, 1])

    def test_propagate_true(self):
        # Given
        c = Clause([1, -2, 5])
        assignments = {1: True, 2: None, 5: None}

        # When
        unit = c.propagate(assignments, -1)

        # Then
        self.assertIsNone(unit)
        self.assertItemsEqual(c.lits, [1, -2, 5])

    def test_propagate_unit(self):
        # Given
        c = Clause([1, -2, 5])
        assignments = {1: False, 2: True, 5: False}

        # When
        unit = c.propagate(assignments, 2)

        # Then
        self.assertEqual(unit, 1)
        self.assertItemsEqual(c.lits, [1, -2, 5])


class TestSolver(unittest.TestCase):

    @mock.patch.object(Solver, 'enqueue')
    def test_add_empty_clause(self, mock_enqueue):
        # Given
        s = Solver()

        # When
        s.add_clause([])

        # Then
        self.assertFalse(s.status)
        self.assertEqual(len(s.watches), 0)
        self.assertEqual(len(s.clauses), 0)
        self.assertFalse(mock_enqueue.called)

    @mock.patch.object(Solver, 'enqueue')
    def test_add_unit_clause(self, mock_enqueue):
        # Given
        s = Solver()

        # When
        s.add_clause([-1])

        # Then
        self.assertIsNone(s.status)
        self.assertEqual(len(s.watches), 0)
        self.assertEqual(len(s.clauses), 0)
        self.assertTrue(mock_enqueue.called)

    @mock.patch.object(Solver, 'enqueue')
    def test_add_clause(self, mock_enqueue):
        # Given
        s = Solver()
        clause = [-1, 2, 4]

        # When
        s.add_clause(clause)

        # Then
        self.assertIsNone(s.status)

        self.assertEqual(len(s.watches), 2)
        self.assertItemsEqual(s.watches[1], [clause])
        self.assertItemsEqual(s.watches[-2], [clause])

        self.assertEqual(len(s.clauses), 1)
        self.assertFalse(mock_enqueue.called)

    @mock.patch.object(Solver, 'enqueue')
    def test_propagate_one_level(self, mock_enqueue):
        # Make one literal true, and check that the watch lists are updated
        # appropriately. We do only one assignment and all the clauses have
        # length 3, so there is no unit information.

        # Given
        s = Solver()
        cl1 = Clause([1, 2, -5])
        cl2 = Clause([2, -4, 7])
        cl3 = Clause([-2, -5, 7])
        s.add_clause(cl1)
        s.add_clause(cl2)
        s.add_clause(cl3)

        s.assignments = {1: None, 2: None, 4: None, 5: None, 7: None}

        # When
        s.assignments[2] = False  # Force 2 to be false.
        s.prop_queue.append(-2)
        conflict = s.propagate()

        # Then
        self._assertWatchesNotTrue(s.watches, s.assignments)
        self.assertFalse(mock_enqueue.called)
        self.assertIsNone(conflict)
        self.assertItemsEqual(s.watches[-7], [cl2])
        self.assertItemsEqual(s.watches[-1], [cl1])
        self.assertItemsEqual(s.watches[2], [cl3])
        self.assertItemsEqual(s.watches[4], [cl2])
        self.assertItemsEqual(s.watches[5], [cl1, cl3])

    @mock.patch.object(Solver, 'enqueue')
    def test_propagate_with_unit_info(self, mock_enqueue):
        # Make one literal true. Since there is one length-2 clause, this will
        # propagate one literal.

        # Given
        s = Solver()
        cl1 = Clause([1, 2, -5])
        cl2 = Clause([2, -4])
        s.add_clause(cl1)
        s.add_clause(cl2)

        s.assignments = {1: None, 2: None, 4: None, 5: None}

        # When
        s.assignments[2] = False  # Force 2 to be false.
        s.prop_queue.append(-2)
        conflict = s.propagate()

        # Then
        self._assertWatchesNotTrue(s.watches, s.assignments)
        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertIsNone(conflict)
        self.assertItemsEqual(s.watches[-2], [cl2])
        self.assertItemsEqual(s.watches[-1], [cl1])
        self.assertItemsEqual(s.watches[4], [cl2])
        self.assertItemsEqual(s.watches[5], [cl1])

    def test_propagate_conflict(self):
        # Make one literal true, and cause a conflict in the unit propagation.

        # Given
        s = Solver()
        cl1 = Clause([-1, 2])
        cl2 = Clause([-1, 2, 3, 4])
        s.add_clause(cl1)
        s.add_clause(cl2)

        s.assignments = {1: True, 2: None, 3: None, 4: None}

        # When
        s.assignments[2] = False  # Force 2 to be false.
        s.prop_queue.append(-2)
        conflict = s.propagate()

        # Then
        self.assertEqual(conflict, cl1)
        # Assert that all clauses are still watched.
        self.assertItemsEqual(s.watches[-3], [cl2])
        self.assertItemsEqual(s.watches[-2], [cl1])
        self.assertItemsEqual(s.watches[1], [cl1, cl2])

    def _assertWatchesNotTrue(self, watches, assignments):
        for watch, clauses in watches.items():
            if len(clauses) > 0:
                status = assignments[abs(watch)]
                self.assertIsNot(status, True)

    def test_enqueue(self):
        # Given
        s = Solver()
        s.assignments = {1: True, 2: None}

        # When / then
        status = s.enqueue(1)
        self.assertTrue(status)
        status = s.enqueue(-1)
        self.assertFalse(status)
        status = s.enqueue(2)
        self.assertTrue(status)
        self.assertItemsEqual(s.prop_queue, [2])

    def test_propagation_with_queue(self):
        # Given
        s = Solver()
        cl1 = Clause([1, 2])
        cl2 = Clause([1, 3, 4])
        s.add_clause(cl1)
        s.add_clause(cl2)
        s.assignments = {1: None, 2: None, 3: None, 4: None}

        # When
        s.enqueue(-2)
        conflict = s.propagate()

        # Then
        self.assertIsNone(conflict)
        self.assertEqual(s.assignments, {1: True, 2: False, 3: None, 4: None})
        self.assertItemsEqual(s.watches[-1], [cl1, cl2])
        self.assertItemsEqual(s.watches[-2], [cl1])
        self.assertItemsEqual(s.watches[-3], [cl2])

    def test_propagation_with_queue_multiple_implications(self):
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
        s.enqueue(-1)
        conflict = s.propagate()

        # Then
        self.assertIsNone(conflict)
        self.assertEqual(s.assignments,
                         {1: False, 2: False, 3: False, 4: False})

    def test_propagation_with_queue_conflicted(self):
        # Check that we can recover from a conflict that arises during unit
        # propagation (i.e. leave the watch list in a consistent state, and
        # return the appropriate conflict clause).

        # Given
        s = Solver()
        cl1 = Clause([1, -2])
        cl2 = Clause([1,  2, -3])
        cl3 = Clause([1,  2,  3, -4])
        s.add_clause(cl1)
        s.add_clause(cl2)
        s.add_clause(cl3)
        s.assignments = {1: None, 2: None, 3: None, 4: True}

        # When
        s.enqueue(-1)
        conflict = s.propagate()

        # Then
        self.assertIsNotNone(conflict)
        self.assertItemsEqual(s.watches[-3], [cl3])
        self.assertItemsEqual(s.watches[-2], [cl2, cl3])
        self.assertItemsEqual(s.watches[-1], [cl1])
        self.assertItemsEqual(s.watches[2], [cl1])
        self.assertItemsEqual(s.watches[3], [cl2])

if __name__ == '__main__':
    unittest.main()
