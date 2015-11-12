import abc
from collections import Counter
from functools import partial

import six

from enstaller.collections import DefaultOrderedDict
from .priority_queue import PriorityQueue, GroupPrioritizer


class IPolicy(six.with_metaclass(abc.ABCMeta)):

    @abc.abstractmethod
    def add_requirements(self, package_ids):
        """ Submit packages to the policy for consideration.
        """

    @abc.abstractmethod
    def get_next_package_id(self, assignments, clauses):
        """ Returns a undecided variable (i.e. integer > 0) for the given sets
        of assignments and clauses.

        Parameters
        ----------
        assignments : OrderedDict
            The current assignments of each literal. Keys are variables
            (integer > 0) and values are one of (True, False, None).
        clauses : List of Clause
            The collection of Clause objects to satisfy.
        """


class PolicyLogger(IPolicy):

    def __init__(self, PolicyFactory, pool, installed_repository):
        self._policy = PolicyFactory(pool, installed_repository)
        self._log_installed = list(installed_repository.iter_packages())
        self._log_suggestions = []
        self._log_required = []
        self._log_pool = pool
        self._log_assignment_changes = []

    def get_next_package_id(self, assignments, clauses):
        self._log_assignment_changes.append(assignments.get_changelog())
        pkg_id = self._policy.get_next_package_id(assignments, clauses)
        self._log_suggestions.append(pkg_id)
        return pkg_id

    def add_requirements(self, package_ids):
        self._log_required.extend(package_ids)
        self._policy.add_requirements(package_ids)

    def _log_histogram(self, pkg_ids):
        c = Counter(pkg_ids)
        lines = (
            "{:>25} {}".format(self._log_pretty_pkg_id(k), v)
            for k, v in sorted(c.items(), key=lambda p: p[1])
        )
        pretty = '\n'.join(lines)
        return c, pretty

    def _log_pretty_pkg_id(self, pkg_id):
        p = self._log_pool._id_to_package[pkg_id]
        return '{} {}'.format(p.name, p.version)


class DefaultPolicy(IPolicy):

    def __init__(self, *args):
        pass

    def add_requirements(self, assignments):
        pass

    def get_next_package_id(self, assignments, _):
        # Given a dictionary of partial assignments, get an undecided variable
        # to be decided next.
        undecided = (
            package_id for package_id, status in six.iteritems(assignments)
            if status is None
        )
        return next(undecided)


class UndeterminedClausePolicy(IPolicy):

    """ An IPolicy that gathers all undetermined packages from clauses whose
    truth value is not yet known and suggests them in descending order by
    package version number. """

    def __init__(self, pool, installed_repository):
        self._pool = pool
        self._installed_map = set(
            pool.package_id(package) for package in
            installed_repository.iter_packages()
        )
        self._decision_set = self._installed_map.copy()

    def add_requirements(self, package_ids):
        for package_id in package_ids:
            self._decision_set.add(package_id)

    def get_next_package_id(self, assignments, clauses):
        """Get the next unassigned package.
        """

        decision_set = self._decision_set
        if len(decision_set) == 0:
            decision_set, candidate_id = \
                self._handle_empty_decision_set(assignments, clauses)
            if candidate_id is not None:
                return candidate_id

        installed_packages, new_package_map = \
            self._group_packages_by_name(decision_set)
        if len(installed_packages) > 0:
            candidate = installed_packages[0]
        else:
            candidate_name = six.next(six.iterkeys(new_package_map))
            candidates = new_package_map[candidate_name]
            candidate = max(candidates, key=lambda package: package.version)

        candidate_id = self._pool.package_id(candidate)

        assert assignments[candidate_id] is None, \
            "Trying to assign to a variable which is already assigned."

        # Clear out decision set.
        self._decision_set = set()
        return candidate_id

    def _group_packages_by_name(self, decision_set):
        installed_packages = []
        new_package_map = DefaultOrderedDict(list)

        for package_id in sorted(decision_set):
            package = self._pool._id_to_package[package_id]
            if package_id in self._installed_map:
                installed_packages.append(package)
            else:
                new_package_map[package.name].append(package)

        return installed_packages, new_package_map

    def _handle_empty_decision_set(self, assignments, clauses):
        # TODO inefficient and verbose

        # The assignments with value None
        unassigned_ids = set(
            literal for literal, status in six.iteritems(assignments)
            if status is None
        )
        # The rest (true and false)
        assigned_ids = set(assignments.keys()) - unassigned_ids

        # Magnitude is literal, sign is Truthiness
        signed_assignments = set()
        for variable in assigned_ids:
            if assignments[variable]:
                signed_assignments.add(variable)
            else:
                signed_assignments.add(-variable)

        for clause in clauses:
            # TODO Need clause.undecided_literals property
            if not signed_assignments.isdisjoint(clause.lits):
                # Clause is true
                continue

            literals = clause.lits
            undecided = unassigned_ids.intersection(literals)

            # The set of relevant literals still undecided
            self._decision_set.update(abs(lit) for lit in undecided)

        if len(self._decision_set) == 0:
            # This will happen if the remaining packages are irrelevant for
            # the set of rules that we're trying to satisfy. In that case,
            # just return one of the undecided IDs.

            # We use min to ensure determinisism
            return self._decision_set, -min(unassigned_ids)
        else:
            return self._decision_set, None


class PriorityQueuePolicy(IPolicy):

    """ An IPolicy that uses a priority queue to determine which package id
    should be suggested next.

    Packages are split into groups:

        1. currently installed,
        2. explicitly specified as a requirement,
        3. everything else,

    where each group is arranged in descending order by version number.
    The groups are searched in order and the first unassigned package id is
    suggested.
    """

    def __init__(self, pool, installed_repository, prefer_installed=True):
        def key_func(p):
            return pool._id_to_package[p].version

        self._unassigned_pkg_ids = PriorityQueue()

        self.DEFAULT = 0
        if prefer_installed:
            self.INSTALLED = -2
            self.REQUIRED = -1
        else:
            self.INSTALLED = -1
            self.REQUIRED = -2

        self._prioritizer = GroupPrioritizer(key_func)
        installed_ids = list(map(pool.package_id, installed_repository))
        self._prioritizer.update(installed_ids, self.INSTALLED)

    def add_requirements(self, package_ids):
        self._add_packages(package_ids, self.REQUIRED)

    def _add_packages(self, package_ids, group):
        prioritizer = self._prioritizer
        prioritizer.update(package_ids, group=group)
        for pkg_id in prioritizer.group(group):
            if pkg_id in self._unassigned_pkg_ids:
                self._unassigned_pkg_ids.push(pkg_id, prioritizer[pkg_id])

    def get_next_package_id(self, assignments, clauses):
        self._update_cache_from_assignments(assignments)

        # Grab the most interesting looking currently unassigned id
        return self._unassigned_pkg_ids.peek()

    def _update_cache_from_assignments(self, assignments):
        changelog = assignments.consume_changelog()

        pkg_ids = set(changelog.keys())
        unknown_ids = pkg_ids.difference(self._prioritizer.known)
        if unknown_ids:
            # We only want to update priorities, we'll decide who is unassigned
            # and who isn't later
            self._prioritizer.update(unknown_ids, group=self.DEFAULT)

        for key, (old, new) in six.iteritems(changelog):
            if new is None:
                # Newly unassigned
                priority = self._prioritizer[key]
                self._unassigned_pkg_ids.push(key, priority=priority)
            elif old is None:
                # No longer unassigned (because new is not None)
                self._unassigned_pkg_ids.remove(key)

        # The remaining case is either True -> False or False -> True, which is
        # probably not possible and we don't care about anyway, or
        # MISSING -> (True|False)

        # A very cheap sanity check
        ours = len(self._unassigned_pkg_ids)
        theirs = len(assignments) - assignments.num_assigned
        assert ours == theirs, "We failed to track variable assignments"


InstalledFirstPolicy = partial(PolicyLogger, PriorityQueuePolicy)
