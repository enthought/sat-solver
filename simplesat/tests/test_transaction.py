#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from ..transaction import Transaction, FailureOperation


class TestTransaction(unittest.TestCase):

    def setUp(self):
        self.t = Transaction(None, [], [])

    def test_failure_operation(self):
        reason = "Everything is fine."
        self.t.fail(reason)
        self.assertIsInstance(self.t.operations[0], FailureOperation)
        self.assertEqual(self.t.operations[0].reason, reason)

    def test_failed(self):
        self.assertFalse(self.t.failed)
        self.t.fail(None)
        self.assertTrue(self.t.failed)

    def test_no_failure_after_install(self):
        self.t.install(None)
        with self.assertRaises(ValueError):
            self.t.fail("It's too late to fail now!")

    def test_no_failure_after_remove(self):
        self.t.remove(None)
        with self.assertRaises(ValueError):
            self.t.fail("It's too late to fail now!")

    def test_no_failure_after_update(self):
        self.t.update(None, None)
        with self.assertRaises(ValueError):
            self.t.fail("It's too late to fail now!")

    def test_no_other_ops_after_failure(self):
        self.t.fail("No operations after this one.")

        with self.assertRaises(ValueError):
            self.t.install(None)

        with self.assertRaises(ValueError):
            self.t.remove(None)

        with self.assertRaises(ValueError):
            self.t.update(None, None)
