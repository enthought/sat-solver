# -*- coding: utf-8 -*-

from collections import defaultdict

import six

from simplesat.constraints.requirement import Requirement
from simplesat.utils import DefaultOrderedDict, toposort, transitive_neighbors
from simplesat.priority_queue import PriorityQueue, GroupPrioritizer
from .policy import IPolicy
from .policy_logger import PolicyLogger


class PriorityQueuePolicy(IPolicy):

    """ An IPolicy that uses a priority queue to determine which package id
    should be suggested next.

    Packages are split into groups:

        1. currently installed,
        2. explicitly specified as a requirement,
        3. everything else,

    where each group is arranged in topological order by dependency
    relationships and then descending order by version number.
    The groups are then searched in order and the first unassigned package id
    is suggested.
    """

    def __init__(self, pool, installed_repository, prefer_installed=True):
        self._pool = pool
        self._installed_ids = set(map(pool.package_id, installed_repository))

        package_ids = pool._id_to_package.keys()
        self._package_id_to_rank = None  # set the first time we check
        self._all_ids = set(package_ids)
        self._required_ids = set()
        self._name_to_package_ids = self._group_packages_by_name(package_ids)

        def priority_func(p):
            return self._package_id_to_rank[p]

        self._unassigned_pkg_ids = PriorityQueue()

        self.DEFAULT = 0
        if prefer_installed:
            self.INSTALLED = -2
            self.REQUIRED = -1
        else:
            self.REQUIRED = -1
            self.INSTALLED = self.DEFAULT

        self._prioritizer = GroupPrioritizer(priority_func)
        self._add_packages(self._installed_ids.copy(), self.INSTALLED)

    def add_requirements(self, package_ids):
        self._required_ids.update(package_ids)
        if self.REQUIRED < self.INSTALLED:
            self._installed_ids.difference_update(package_ids)
        else:
            package_ids = set(package_ids).difference(self._installed_ids)
        self._add_packages(package_ids, self.REQUIRED)

    def get_next_package_id(self, assignments, clauses):
        self._update_cache_from_assignments(assignments)
        # Grab the most interesting looking currently unassigned id
        p_id = self._unassigned_pkg_ids.peek()
        return p_id

    def _add_packages(self, package_ids, group):
        prioritizer = self._prioritizer
        prioritizer.update(package_ids, group=group)

        # Removing an item from an ordering always maintains the ordering,
        # so we only need to update priorities on groups that had items added
        for pkg_id in prioritizer.group(group):
            if pkg_id in self._unassigned_pkg_ids:
                self._unassigned_pkg_ids.push(pkg_id, prioritizer[pkg_id])

    def pkg_key(self, package_id):
        """ Return the key used to compare two packages. """
        package = self._pool._id_to_package[package_id]
        try:
            installed = package.repository_info.name == 'installed'
        except AttributeError:
            installed = False
        return (package.version, installed)

    def _rank_packages(self, package_ids):
        """ Return a dictionary of package_id to priority rank.

        Currently we build a dependency tree of all the relevant packages and
        then rank them topologically, starting with those at the top.

        This strategy causes packages which force more assignments via
        unit propagation in the solver to be preferred.
        """
        pool = self._pool
        R = Requirement

        # The direct dependencies of each package
        dependencies = defaultdict(set)
        for package_id in package_ids:
            dependencies[package_id].update(
                pool.package_id(package)
                for cons in pool._id_to_package[package_id].install_requires
                for package in pool.what_provides(R.from_constraints(cons))
            )

        # This is a flattened version of `dependencies` above
        transitive = transitive_neighbors(dependencies)

        packages_by_name = self._group_packages_by_name(package_ids)

        # Some packages have unversioned dependencies, such as simply 'pandas'.
        # This can produce cycles in the dependency graph which much be removed
        # before topological sorting can be done.
        # The strategy is to ignore the dependencies of any package that is
        # present in its own transitive dependency list
        removed_deps = []
        for package_id in package_ids:
            package = pool._id_to_package[package_id]
            deps = dependencies[package_id]
            package_group = packages_by_name[package.name]
            for dep in list(deps):
                circular = transitive[dep].intersection(package_group)
                if circular:
                    packages = [pool._id_to_package[p] for p in circular]
                    depkg = pool._id_to_package[dep]
                    pkg_strings = [
                        "{}-{}".format(pkg.name, pkg.version)
                        for pkg in packages
                    ]
                    msg = "Circular Deps: {}-{} -> {}-{} -> {}".format(
                        package.name, package.version,
                        depkg.name, depkg.version,
                        pkg_strings
                    )
                    removed_deps.append(msg)
                    deps.remove(dep)

        # Mark packages as depending on older versions of themselves so that
        # they will come out first in the toposort
        for package_id in package_ids:
            package = pool._id_to_package[package_id]
            package_group = packages_by_name[package.name]
            idx = package_group.index(package_id)
            other_older = package_group[:idx + 1]
            dependencies[package_id].update(other_older)

        # Finally toposort the packages, preferring higher version and
        # already-installed packages to break ties
        ordered = [
            package_id
            for group in tuple(toposort(dependencies))
            for package_id in sorted(group, key=self.pkg_key, reverse=True)
        ]

        package_id_to_rank = {
            package_id: rank
            for rank, package_id in enumerate(ordered)
        }

        return package_id_to_rank

    def _group_packages_by_name(self, package_ids):
        """ Return a dictionary from package name to all package ids
        corresponding to packages with that name. """
        pool = self._pool

        name_map = DefaultOrderedDict(list)
        for package_id in package_ids:
            package = pool._id_to_package[package_id]
            name_map[package.name].append(package_id)

        name_to_package_ids = {}

        for name, package_ids in name_map.items():
            ordered = sorted(package_ids, key=self.pkg_key, reverse=True)
            name_to_package_ids[name] = ordered

        return name_to_package_ids

    def _update_cache_from_assignments(self, assignments):
        new_keys = assignments.new_keys.copy()
        changelog = assignments.consume_changelog()

        if new_keys:
            unknown_ids = new_keys.difference(self._prioritizer.known)
            self._all_ids.update(new_keys)
            self._package_id_to_rank = self._rank_packages(self._all_ids)
            self._prioritizer.update(unknown_ids, group=self.DEFAULT)

            # Newly unassigned
            self._unassigned_pkg_ids.clear()
            for key in assignments.unassigned_ids:
                priority = self._prioritizer[key]
                self._unassigned_pkg_ids.push(key, priority=priority)
        else:
            for key, (old, new) in six.iteritems(changelog):
                if new is None:
                    # Newly unassigned
                    priority = self._prioritizer[key]
                    self._unassigned_pkg_ids.push(key, priority=priority)
                elif old is None:
                    # No longer unassigned (because new is not None)
                    self._unassigned_pkg_ids.remove(key)

            # The remaining case is True -> False, False -> True or
            # MISSING -> (True|False)

        # A very cheap sanity check
        ours = len(self._unassigned_pkg_ids)
        theirs = len(assignments) - assignments.num_assigned
        has_new_keys = len(new_keys)
        msg = "We failed to track variable assignments {} {} {}"
        assert ours == theirs, msg.format(ours, theirs, has_new_keys)


def LoggedPriorityQueuePolicty(pool, installed_repository, *args, **kwargs):
    policy = PriorityQueuePolicy(pool, installed_repository, *args, **kwargs)
    logger = PolicyLogger(policy, extra_args=args, extra_kwargs=kwargs)
    return logger
