#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict

import six


class _MISSING(object):
    def __str__(self):
        return '<MISSING>'
MISSING = _MISSING()


class AssignmentSet(object):

    """A collection of literals and their assignments."""

    def __init__(self, assignments=None):
        # Changelog is a dict of id -> (original value, new value)
        # FIXME: Verify that we really need ordering here
        self._data = OrderedDict()
        self._orig = {}
        self._cached_changelog = None
        self._assigned_literals = set()
        self.has_new_keys = False
        for k, v in (assignments or {}).items():
            self[k] = v

    def __setitem__(self, key, value):
        assert key > 0

        prev_value = self._data.get(key, MISSING)

        if prev_value is MISSING:
            self.has_new_keys = True
            prev_value = None
        elif prev_value is not None:
            self._assigned_literals.difference_update((key, -key))

        if value is not None:
            self._assigned_literals.add(key if value else -key)

        self._update_diff(key, value)
        self._data[key] = value

    def __delitem__(self, key):
        self._update_diff(key, MISSING)
        prev = self._data.pop(key)
        if prev is not None:
            self._assigned_literals.difference_update((key, -key))

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, key):
        return key in self._data

    def items(self):
        return list(self._data.items())

    def iteritems(self):
        return six.iteritems(self._data)

    def keys(self):
        return list(self._data.keys())

    def values(self):
        return list(self._data.values())

    def _update_diff(self, key, value):
        prev = self._data.get(key, MISSING)
        self._orig.setdefault(key, prev)
        # If a value changes, dump the cached changelog
        self._cached_changelog = None

    def get_changelog(self):
        if self._cached_changelog is None:
            self._cached_changelog = {
                key: (old, new)
                for key, old in six.iteritems(self._orig)
                for new in [self._data.get(key, MISSING)]
                if new != old
            }
        return self._cached_changelog

    def consume_changelog(self):
        old = self.get_changelog()
        self._orig = {}
        self._cached_changelog = {}
        self.has_new_keys = False
        return old

    def copy(self):
        new = AssignmentSet()
        new._data = self._data.copy()
        new._orig = self._orig.copy()
        new._assigned_literals = self._assigned_literals.copy()
        new.has_new_keys = self.has_new_keys
        return new

    def value(self, lit):
        """ Return the value of literal in terms of the positive. """
        if lit in self._assigned_literals:
            return True
        elif -lit in self._assigned_literals:
            return False
        else:
            return None

    @property
    def num_assigned(self):
        return len(self._assigned_literals)
