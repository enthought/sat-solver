#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

from collections import defaultdict

import six


def toposort(nodes_to_edges):
    """Dependencies are expressed as a dictionary whose keys are items and
    whose values are a set of dependent items. Output is a list of sets in
    topological order. The first set consists of items with no dependences,
    each subsequent set consists of items that depend upon items in the
    preceeding sets.

    >>> print '\\n'.join(repr(sorted(x)) for x in toposort2({
        ...     2: set([11]),
        ...     9: set([11,8]),
        ...     10: set([11,3]),
        ...     11: set([7,5]),
        ...     8: set([7,3]),
        ...     }) )
    [3, 5, 7]
    [8, 11]
    [2, 9, 10]

    """

    data = {k: v.copy() for k, v in six.iteritems(nodes_to_edges)}

    # Ignore self dependencies.
    for k, v in six.iteritems(data):
        v.discard(k)

    # Find all items that don't depend on anything.
    extra_items_in_deps = six.functools.reduce(set.union, six.itervalues(data))
    extra_items_in_deps.difference_update(set(six.iterkeys(data)))

    # Add empty dependences where needed
    data.update({item: set() for item in extra_items_in_deps})

    while True:
        ordered = set(item for item, dep in six.iteritems(data) if not dep)
        if not ordered:
            break
        yield ordered
        data = {item: (dep - ordered)
                for item, dep in six.iteritems(data)
                if item not in ordered}
    if data:
        msg = "Cyclic dependencies exist among these items:\n{}"
        cyclic = '\n'.join(repr(x) for x in six.iteritems(data))
        raise ValueError(msg.format(cyclic))


def transitive_neighbors(nodes_to_edges):
    """ Return the set of all reachable nodes for each node in the
    nodes_to_edges adjacency dict. """
    trans = defaultdict(set)
    for node in nodes_to_edges.keys():
        _transitive(node, nodes_to_edges, trans)
    return trans


def _transitive(node, nodes_to_edges, trans):
    trans = trans if trans is not None else defaultdict(set)
    if node in trans:
        return trans
    neighbors = nodes_to_edges[node]
    trans[node].update(neighbors)
    for neighbor in neighbors:
        _transitive(neighbor, nodes_to_edges, trans)
        trans[node].update(trans[neighbor])
    return trans
