import abc

from collections import Counter
from functools import partial
from itertools import count

import six

from enstaller.collections import DefaultOrderedDict

from .priority_queue import PriorityQueue


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


class PolicyLogger(IPolicy):

    def __init__(self, PolicyFactory, pool, installed_repository):
        self._policy = PolicyFactory(pool, installed_repository)
        self._log_installed = list(installed_repository.iter_packages())
        self._log_suggestions = []
        self._log_required = []
        self._log_pool = pool
        self._log_assignment_changes = []

    def get_next_package_id(self, assignments, clauses):
        self._log_assignment_changes.append(assignments._changelog.copy())
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


class _InstalledFirstPolicy(IPolicy):

    CURRENT = count(-2e10)
    REQUIRED = count(-1e10)

    def __init__(self, pool, installed_repository):
        self._pool = pool
        self._installed_pkg_ids = set(
            pool.package_id(package) for package in
            installed_repository.iter_packages()
        )
        self._seen_pkg_ids = set()
        self._required_pkg_ids = set()
        self._pkg_id_priority = {}
        self._unassigned_pkg_ids = PriorityQueue()

    def _update_pkg_id_priority(self, assignments=None):
        assignments = assignments or {}
        pkg_id_priority = {}
        self._seen_pkg_ids.update(assignments.keys())

        ordered_pkg_ids = sorted(
            self._seen_pkg_ids,
            key=lambda p: self._pool._id_to_package[p].version,
            reverse=True,
        )

        for priority, pkg_id in enumerate(ordered_pkg_ids):

            # Determine the new priority of this pkg
            if pkg_id in self._required_pkg_ids:
                new = next(self.REQUIRED)
            elif pkg_id in self._installed_pkg_ids:
                new = next(self.CURRENT)
            else:
                new = priority

            if pkg_id in self._unassigned_pkg_ids:
                self._unassigned_pkg_ids.push(pkg_id, priority=new)

            pkg_id_priority[pkg_id] = new
        self._pkg_id_priority = pkg_id_priority

    def add_requirements(self, package_ids):
        self._required_pkg_ids.update(package_ids)
        self._seen_pkg_ids.update(package_ids)
        self._update_pkg_id_priority()

    def get_next_package_id(self, assignments, clauses):
        self._update_cache_from_assignments(assignments)

        # Grab the most interesting looking currently unassigned id
        return self._unassigned_pkg_ids.peek()

    def _update_cache_from_assignments(self, assignments):
        for key, (old, new) in six.iteritems(assignments.consume_changelog()):
            if key not in self._seen_pkg_ids:
                self._update_pkg_id_priority(assignments)
            if new is None:
                # Newly unassigned
                priority = self._pkg_id_priority[key]
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


InstalledFirstPolicy = partial(PolicyLogger, _InstalledFirstPolicy)


class OldInstalledFirstPolicy(IPolicy):

    def __init__(self, pool, installed_repository):
        self._pool = pool
        self._installed_map = set(
            pool.package_id(package) for package in
            installed_repository.iter_packages()
        )
        self._decision_set = self._installed_map.copy()

    def add_requirements(self, package_ids):
        # TODO Just make this add_requirement.
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
