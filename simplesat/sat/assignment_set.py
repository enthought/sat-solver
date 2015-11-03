#!/usr/bin/env python
# -*- coding: utf-8 -*-


import six

from collections import OrderedDict


class _MISSING(object):
    pass
MISSING = _MISSING()


class AssignmentSet(object):

    """A collection of literals and their assignments."""

    def __init__(self):
        self._nassigned = 0
        # Changelog is a dict of id -> (original value, new value)
        # FIXME: Verify that we really need ordering here
        self._data = OrderedDict()
        self._changelog = {}

    def __setitem__(self, key, value):
        assert key >= 0

        prev_value = self.get(key)

        if prev_value is not None:
            self._nassigned -= 1

        if value is not None:
            self._nassigned += 1

        self._update_changelog(key, value)
        self._data[key] = value

    def __delitem__(self, key):
        self._update_changelog(key, MISSING)
        prev = self._data.pop(key)
        if prev is not None:
            self._nassigned -= 1

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __len__(self):
        return len(self._data)

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

    def _update_changelog(self, key, value):
        if key in self._changelog:
            orig = self._changelog[key][0]
        elif key in self._data:
            orig = self._data[key]
        else:
            orig = MISSING

        if orig == value:
            self._changelog.pop(key, None)
        else:
            self._changelog[key] = (orig, value)

    def get_changelog(self):
        return self._changelog.copy()

    def consume_changelog(self):
        old = self._changelog
        self._changelog = {}
        return old

    def copy(self):
        new = AssignmentSet()
        new._data = self._data.copy()
        new._changelog = self._changelog.copy()
        new._nassigned = self._nassigned
        return new

    @property
    def num_assigned(self):
        return self._nassigned
