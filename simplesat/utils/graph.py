#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

from collections import defaultdict

import six
import itertools

from simplesat.constraints.requirement import Requirement


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
    extra_items_in_deps = set(
        itertools.chain.from_iterable(six.itervalues(data)))
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


def package_lit_dependency_graph(pool, package_lits, closed=True):
    """
    Return an dict of nodes to edges from package_lits to their dependencies,
    maintaining sign.

    If closed is True, only include edges to packages in package_lits.
    """

    package_id_map = {abs(p): p for p in package_lits}
    packages = {package_id: pool._id_to_package[abs(package_id)]
                for package_id in package_lits}

    R = Requirement.from_constraints
    nodes_to_edges = {package_id: set() for package_id in package_lits}

    for package_lit, package in packages.items():
        for constraints in package.install_requires:
            deps = pool.what_provides(R(constraints))
            nodes_to_edges[package_lit].update(
                dep_lit for dep_lit in (
                    package_id_map.get(dep_id, dep_id)
                    for dep_id in (pool.package_id(dep) for dep in deps)
                    if (not closed or dep_id in package_id_map)
                )
            )

    return dict(nodes_to_edges)


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
