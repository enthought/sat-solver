#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import unittest

from ..priority_queue import PriorityQueue, REMOVED_TASK


def assert_raises(exception, f, *args, **kwargs):
    try:
        f(*args, **kwargs)
    except exception:
        return
    msg = "{}(*{}, **{}) did not raise {}"
    raise AssertionError(msg.format(f, args, kwargs, exception))


class TestPriorityQueue(unittest.TestCase):

    def setUp(self):
        self.N = 250
        self.priorities = random.sample(range(self.N * 2), self.N)
        random.shuffle(self.priorities)

    def test_insert_pop(self):
        pq = PriorityQueue()
        items = list(enumerate(self.priorities))

        for p, task in items:
            pq.push(task, priority=p)

        result = pq.pop_many()

        self.assertEqual(len(pq), 0)
        self.assertFalse(pq)

        expected = [x[1] for x in sorted(items)]

        self.assertEqual(result, expected)

    def test_len_remove_discard(self):
        pq = PriorityQueue()
        for t, p in enumerate(self.priorities):
            self.assertEqual(len(pq), t)
            pq.push(t, priority=p)
        self.assertEqual(len(pq), self.N)

        for t in range(self.N):
            self.assertEqual(len(pq), self.N - t)
            if t % 2:
                pq.remove(t)
            else:
                pq.discard(t)
        self.assertEqual(len(pq), 0)

    def test_len_pop(self):
        pq = PriorityQueue()
        for t, p in enumerate(self.priorities):
            self.assertEqual(len(pq), t)
            pq.push(t, priority=p)
        self.assertEqual(len(pq), self.N)

        for t in range(self.N):
            self.assertEqual(len(pq), self.N - t)
            pq.pop()
        self.assertEqual(len(pq), 0)

    def test_bool_full_empty(self):
        pq = PriorityQueue()
        self.assertFalse(pq)

        pq.push(0)
        self.assertTrue(pq)

        pq.push(1)
        self.assertTrue(pq)

        pq.discard(2)
        self.assertTrue(pq)

        pq.discard(1)
        self.assertTrue(pq)

        pq.remove(0)
        self.assertFalse(pq)

    def test_tasks_are_unique(self):
        pq = PriorityQueue()
        pq.push(0)

    def test_peek(self):
        pq = PriorityQueue()

        for i in range(100):
            pq.push(i, priority=i)

        self.assertEqual(0, pq.peek())

        pq.discard(0)
        self.assertEqual(1, pq.peek())
        for i in range(2, 80):
            pq.remove(i)

        self.assertEqual(1, pq.peek())
        self.assertEqual(1, pq.pop())

        self.assertEqual(80, pq.peek())

    def test_no_pop_removed(self):
        pq = PriorityQueue()
        pq.push(0)
        pq.remove(0)
        assert_raises(
            KeyError,
            pq.pop,
        )

    def test_same_priority_stable(self):
        pq = PriorityQueue()
        expected = self.priorities
        for t in expected:
            pq.push(t)
        result = pq.pop_many()
        self.assertEqual(expected, result)

    def test_empty_throws_exceptions(self):
        pq = PriorityQueue()
        assert_raises(
            KeyError,
            pq.pop,
        )
        assert_raises(
            KeyError,
            pq.peek,
        )
        assert_raises(
            KeyError,
            pq.remove,
            0,
        )
        self.assertEqual([], pq.pop_many())

    def test_contains(self):
        pq = PriorityQueue()

        pq.push(0)
        self.assertIn(0, pq)
        pq.push(0)
        self.assertIn(0, pq)

        pq.push(1)
        self.assertIn(0, pq)
        self.assertIn(1, pq)

        pq.remove(0)
        self.assertIn(1, pq)
        self.assertNotIn(0, pq)

        pq.pop()
        self.assertNotIn(0, pq)
        self.assertNotIn(1, pq)

    def test_barrage(self):
        pq = PriorityQueue()

        has = set()

        for t, p in enumerate(self.priorities):
            pq.push(t, priority=p)
            has.add(t)

        for i in range(20000):

            self.assertEqual(len(pq), len(has))

            t = random.choice(self.priorities)

            if t not in has:
                self.assertNotIn(t, pq)
                assert_raises(
                    KeyError,
                    pq.remove,
                    t
                )
                pq.discard(t)
            else:
                if random.random() > 0.5:
                    pq.remove(t)
                    has.remove(t)

            if random.random() > 0.5:
                pq.push(t, priority=random.randrange(self.N))
                has.add(t)

            if random.random() > 0.75 and has:
                t = has.pop()
                pq.remove(t)

            if random.random() > 0.75 and has:
                t = pq.peek()
                expected = next(
                    t for t in sorted(pq._pq)
                    if t[2] is not REMOVED_TASK
                )[2]
                self.assertEqual(t, expected)
                self.assertEqual(t, pq.pop())
                has.remove(t)
