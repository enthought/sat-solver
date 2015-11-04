#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from ..assignment_set import AssignmentSet, MISSING


class TestAssignmentSet(unittest.TestCase):

    def test_starts_empty(self):
        AS = AssignmentSet()
        self.assertEqual(AS.num_assigned, 0)
        self.assertEqual(len(AS), 0)
        self.assertEqual({}, AS.get_changelog())
        self.assertEqual([], AS.keys())
        self.assertEqual([], AS.values())
        self.assertEqual([], AS.items())

    def test_num_assigned(self):
        AS = AssignmentSet()

        AS[0] = None
        self.assertEqual(AS.num_assigned, 0)

        AS[1] = True
        self.assertEqual(AS.num_assigned, 1)

        AS[0] = False
        self.assertEqual(AS.num_assigned, 2)

        AS[1] = None
        self.assertEqual(AS.num_assigned, 1)

        AS[1] = True
        self.assertEqual(AS.num_assigned, 2)

        del AS[0]
        self.assertEqual(AS.num_assigned, 1)

        AS[1] = False
        self.assertEqual(AS.num_assigned, 1)

        AS[1] = None
        self.assertEqual(AS.num_assigned, 0)

        del AS[1]
        self.assertEqual(AS.num_assigned, 0)

    def test_container(self):
        AS = AssignmentSet()

        AS[0] = True
        AS[1] = False

        self.assertIn(0, AS)
        self.assertNotIn(2, AS)

        AS[3] = None
        AS[2] = True
        AS[4] = None

        self.assertIn(2, AS)
        self.assertIn(4, AS)

        del AS[4]
        self.assertNotIn(4, AS)

        expected = [(0, True), (1, False), (3, None), (2, True)]

        manual_result = list(zip(AS.keys(), AS.values()))
        self.assertEqual(AS.items(), expected)
        self.assertEqual(manual_result, expected)
        self.assertEqual(len(AS), len(expected))

    def test_copy(self):

        AS = AssignmentSet()

        AS[0] = None
        AS[1] = True
        AS[2] = None
        AS[3] = False
        AS[4] = True

        expected = {
            0: None,
            1: True,
            2: None,
            3: False,
            4: True,
        }

        copied = AS.copy()

        self.assertIsNot(copied._data, AS._data)
        self.assertEqual(copied._data, expected)

        expected = {k: MISSING for k in expected}

        self.assertIsNot(copied._orig, AS._orig)
        self.assertEqual(copied._orig, expected)

        self.assertEqual(copied.num_assigned, AS.num_assigned)

        del AS[1]
        self.assertIn(1, copied)

    def test_changelog(self):

        AS = AssignmentSet()

        AS[0] = None

        expected = {0: (MISSING, None)}
        self.assertEqual(AS.get_changelog(), expected)

        AS[1] = True
        expected[1] = (MISSING, True)
        self.assertEqual(AS.get_changelog(), expected)

        AS[1] = False
        expected[1] = (MISSING, False)
        self.assertEqual(AS.get_changelog(), expected)

        del AS[1]
        del expected[1]
        self.assertEqual(AS.get_changelog(), expected)

        # Keep should preserve the log
        self.assertEqual(AS.get_changelog(), expected)
        self.assertEqual(AS.get_changelog(), expected)

        # Otherwise clear the log
        log = AS.consume_changelog()
        self.assertEqual(log, expected)
        self.assertEqual(AS.get_changelog(), {})

        # Test when something is already present
        AS[0] = False
        expected = {0: (None, False)}
        self.assertEqual(AS.get_changelog(), expected)

        del AS[0]
        expected = {0: (None, MISSING)}
        self.assertEqual(AS.get_changelog(), expected)
