#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import partial
from heapq import heappush, heappop
from itertools import count


class _REMOVED_TASK(object):
    pass
REMOVED_TASK = _REMOVED_TASK()


class PriorityQueue(object):
    """ A priority queue implementation that supports reprioritizing or
    removing tasks, given that tasks are unique.

    Borrowed from: https://docs.python.org/3/library/heapq.html
    """

    def __init__(self):
        # list of entries arranged in a heap
        self._pq = []
        # mapping of tasks to entries
        self._entry_finder = {}
        # unique id genrator for tie-breaking
        self._next_id = partial(next, count())

    def __len__(self):
        return len(self._entry_finder)

    def __bool__(self):
        return bool(len(self))

    def __contains__(self, key):
        return key in self._entry_finder

    def push(self, task, priority=0):
        "Add a new task or update the priority of an existing task"
        return self._push(priority, self._next_id(), task)

    def peek(self):
        """ Return the next task, without popping it. """
        if not self._pq:
            raise KeyError('peek from an empty priority queue')
        entry = self._pq[0]
        if entry[-1] is REMOVED_TASK:
            entry = self._pop()
        self._push(*entry)
        return entry[-1]

    def pop(self):
        'Remove and return the lowest priority task. Raise KeyError if empty.'
        _, _, task = self._pop()
        return task

    def pop_many(self, n=None):
        """ Return a list of length n of popped elements. If n is not
        specified, pop the entire queue. """
        if n is None:
            n = len(self)
        result = []
        for _ in range(n):
            result.append(self.pop())
        return result

    def discard(self, task):
        "Remove an existing task if present. If not, do nothing."
        try:
            self.remove(task)
        except KeyError:
            pass

    def remove(self, task):
        "Remove an existing task. Raise KeyError if not found."
        entry = self._entry_finder.pop(task)
        entry[-1] = REMOVED_TASK

    def _pop(self):
        while self._pq:
            entry = heappop(self._pq)
            if entry[-1] is not REMOVED_TASK:
                del self._entry_finder[entry[-1]]
                return entry
        raise KeyError('pop from an empty priority queue')

    def _push(self, priority, task_id, task):
        if task in self:
            o_priority, _, o_task = self._entry_finder[task]
            # Still check the task, which might now be REMOVED
            if priority == o_priority and task == o_task:
                # We're pushing something we already have, do nothing
                return
            else:
                # Make space for the new entry
                self.remove(task)
        entry = [priority, task_id, task]
        self._entry_finder[task] = entry
        heappush(self._pq, entry)
