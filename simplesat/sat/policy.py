from __future__ import print_function

import abc
from collections import Counter, defaultdict
import sys

import six

from enstaller.collections import DefaultOrderedDict
from enstaller.new_solver.requirement import Requirement
from simplesat.utils.graph import toposort
from .priority_queue import PriorityQueue, GroupPrioritizer


def _pkg_id_to_version(pool, package_id):
    return pool._id_to_package[package_id].version


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
        assignments : AssignmentSet
            The current assignments of each literal. Keys are variables
            (integer > 0) and values are one of (True, False, None).
        clauses : List of Clause
            The collection of Clause objects to satisfy.
        """


class PolicyLogger(IPolicy):

    def __init__(self, policy):
        self._policy = policy
        self._log_pool = policy._pool
        self._log_installed = policy._installed_ids.copy()
        self._log_required = []
        self._log_suggestions = []
        self._log_assignment_changes = []

    def get_next_package_id(self, assignments, clauses):
        self._log_assignment_changes.append(assignments.get_changelog())
        pkg_id = self._policy.get_next_package_id(assignments, clauses)
        self._log_suggestions.append(pkg_id)
        assignments.consume_changelog()
        return pkg_id

    def add_requirements(self, package_ids):
        self._log_required.extend(package_ids)
        self._log_installed.difference_update(package_ids)
        self._policy.add_requirements(package_ids)

    def _log_histogram(self, pkg_ids=None):
        if pkg_ids is None:
            pkg_ids = map(abs, self._log_suggestions)
        c = Counter(pkg_ids)
        lines = (
            "{:>25} {}".format(self._log_pretty_pkg_id(k), v)
            for k, v in c.most_common()
        )
        pretty = '\n'.join(lines)
        return c, pretty

    def _log_pretty_pkg_id(self, pkg_id):
        package = self._log_pool._id_to_package[pkg_id]
        name_ver = '{} {}'.format(package.name, package.version)
        fill = '.' if pkg_id % 2 else ''
        repo = package.repository_info.name
        return "{:{fill}<30} {:3} {}".format(name_ver, pkg_id, repo, fill=fill)

    def _log_report(self, ids=None):

        def pkg_name(pkg_id):
            return pkg_key(pkg_id)[0]

        def pkg_key(pkg_id):
            pkg = self._log_pool._id_to_package[pkg_id]
            return pkg.name, pkg.version

        if ids is None:
            ids = map(abs, self._log_suggestions)
        report = []
        changes = []
        for pkg, change in self._log_assignment_changes[0].items():
            name = self._log_pretty_pkg_id(pkg)
            if change[1] is not None:
                changes.append("{} : {}".format(name, change[1]))
        report.append('\n'.join(changes))

        required = set(self._log_required)
        installed = set(self._log_installed)
        for (i, sugg) in enumerate(ids):
            pretty = self._log_pretty_pkg_id(sugg)
            R = 'R' if sugg in required else ' '
            I = 'I' if sugg in installed else ' '
            changes = []
            try:
                items = self._log_assignment_changes[i + 1].items()
                for pkg, change in sorted(items, key=lambda p: pkg_key(p[0])):
                    if pkg_name(pkg) != pkg_name(sugg):
                        _pretty = self._log_pretty_pkg_id(pkg)
                        fro, to = map(str, change)
                        msg = "{:10} - {:10} : {}"
                        changes.append(msg.format(fro, to, _pretty))
                if changes:
                    changes = '\n\t'.join([''] + changes)
                else:
                    changes = ""
            except IndexError:
                changes = ""
            msg = "{:>4} {}{} - {}{}"
            report.append(msg.format(i, R, I, pretty, changes))
        return '\n'.join(report)


class DefaultPolicy(IPolicy):

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
        self._installed_ids = set(
            pool.package_id(package) for package in installed_repository
        )
        self._decision_set = self._installed_ids.copy()
        self._requirements = set()

    def add_requirements(self, package_ids):
        self._requirements.update(package_ids)

    def get_next_package_id(self, assignments, clauses):
        """Get the next unassigned package.
        """
        candidate_id = (
            self._best_candidate(self._installed_ids, assignments) or
            self._best_candidate(self._requirements, assignments) or
            self._best_candidate(self._decision_set, assignments)
        )

        if candidate_id is None:
            self._decision_set.clear()
            candidate_id = \
                self._handle_empty_decision_set(assignments, clauses)
            if candidate_id is None:
                candidate_id = self._best_candidate(
                    self._decision_set,
                    assignments
                )

        assert assignments[candidate_id] is None, \
            "Trying to assign to a variable which is already assigned."

        return candidate_id

    def _without_assigned(self, package_ids, assignments):
        return package_ids.difference(
            pkg_id for pkg_id in package_ids.copy()
            if assignments[pkg_id] is not None
        )

    def _best_candidate(self, package_ids, assignments):
        by_version = six.functools.partial(_pkg_id_to_version, self._pool)
        unassigned = self._without_assigned(package_ids, assignments)
        try:
            return max(unassigned, key=by_version)
        except ValueError:
            return None

    def _group_packages_by_name(self, decision_set):
        installed_packages = []
        new_package_map = DefaultOrderedDict(list)

        for package_id in sorted(decision_set):
            package = self._pool._id_to_package[package_id]
            if package_id in self._installed_ids:
                installed_packages.append(package)
            else:
                new_package_map[package.name].append(package)

        return installed_packages, new_package_map

    def _handle_empty_decision_set(self, assignments, clauses):
        # TODO inefficient and verbose

        unassigned_ids = set(
            literal for literal, status in six.iteritems(assignments)
            if status is None
        )
        assigned_ids = set(assignments.keys()) - unassigned_ids

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

            variables = map(abs, clause.lits)
            undecided = unassigned_ids.intersection(variables)
            self._decision_set.update(lit for lit in undecided)

        if len(self._decision_set) == 0:
            # This will happen if the remaining packages are irrelevant for
            # the set of rules that we're trying to satisfy. In that case,
            # just return one of the undecided IDs.

            # We use min to ensure determinisism
            return min(unassigned_ids)
        else:
            return None


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

    def transitive_deps(self, pkg, dependencies, trans=None):
        trans = trans if trans is not None else defaultdict(set)
        if pkg in trans:
            return trans
        deps = dependencies[pkg]
        trans[pkg].update(deps)
        for dep in deps:
            self.transitive_deps(dep, dependencies, trans)
            trans[pkg].update(trans[dep])
        return trans

    def _rank_packages(self, package_ids):
        pool = self._pool

        dependencies = defaultdict(set)
        to_req = Requirement.from_legacy_requirement_string
        for package_id in package_ids:
            dependencies[package_id].update(
                pool.package_id(package)
                for dep_str in pool._id_to_package[package_id].dependencies
                for package in pool.what_provides(to_req(dep_str))
            )

        transitive = defaultdict(set)
        for pkg_id in package_ids:
            self.transitive_deps(pkg_id, dependencies, transitive)

        packages_by_name = self._group_packages_by_name(package_ids)

        for package_id in package_ids:
            package = pool._id_to_package[package_id]
            deps = dependencies[package_id]
            group = packages_by_name[package.name]
            for dep in list(deps):
                depkg = pool._id_to_package[dep]
                bad = [pool._id_to_package[p]
                       for p in transitive[dep].intersection(group)]
                if bad:
                    msg = "BAD: {}-{} -> {}-{} -> {}".format(
                        package.name, package.version,
                        depkg.name, depkg.version,
                        ["{}-{}".format(pkg.name, pkg.version) for pkg in bad]
                    )
                    print(msg, file=sys.stderr)
                    deps.remove(dep)

        for package_id in package_ids:
            package = pool._id_to_package[package_id]
            others = pool.what_provides(to_req(package.name))
            other_older = (pool.package_id(other) for other in others
                           if other.version < package.version)
            dependencies[package_id].update(other_older)

        ordered = []
        by_version = six.functools.partial(_pkg_id_to_version, pool)
        for group in reversed(tuple(toposort(dependencies))):
            ordered.extend(sorted(group, key=by_version, reverse=True))

        package_id_to_rank = {
            package_id: rank
            for rank, package_id in enumerate(ordered)
        }

        return package_id_to_rank

    def _group_packages_by_name(self, package_ids):
        pool = self._pool

        name_map = DefaultOrderedDict(list)
        for package_id in package_ids:
            package = pool._id_to_package[package_id]
            name_map[package.name].append(package_id)

        name_to_package_ids = {}
        by_version = six.functools.partial(_pkg_id_to_version, pool)
        for name, package_ids in name_map.items():
            ordered = sorted(package_ids, key=by_version, reverse=True)
            name_to_package_ids[name] = ordered

        return name_to_package_ids

    def __init__(self, pool, installed_repository, prefer_installed=True):
        self._pool = pool
        self._installed_ids = set(map(pool.package_id, installed_repository))

        package_ids = pool._id_to_package.keys()
        package_id_to_rank = self._rank_packages(package_ids)
        self._name_to_package_ids = self._group_packages_by_name(package_ids)

        def key_func(p):
            return package_id_to_rank[p]

        self._unassigned_pkg_ids = PriorityQueue()

        self.DEFAULT = 0
        if prefer_installed:
            self.INSTALLED = -2
            self.REQUIRED = -1
        else:
            self.REQUIRED = -2
            self.INSTALLED = -1

        self._prioritizer = GroupPrioritizer(key_func)
        self._add_packages(self._installed_ids.copy(), self.INSTALLED)

    def add_requirements(self, package_ids):
        self._installed_ids.difference_update(package_ids)
        self._add_packages(package_ids, self.REQUIRED)

    def _add_packages(self, package_ids, group):
        prioritizer = self._prioritizer
        prioritizer.update(package_ids, group=group)

        # Removing an item from an ordering always maintains the ordering,
        # so we only need to update priorities on groups that had items added
        for pkg_id in prioritizer.group(group):
            if pkg_id in self._unassigned_pkg_ids:
                self._unassigned_pkg_ids.push(pkg_id, prioritizer[pkg_id])

    def get_next_package_id(self, assignments, clauses):
        self._update_cache_from_assignments(assignments)

        # Grab the most interesting looking currently unassigned id
        return self._unassigned_pkg_ids.peek()

    def _update_cache_from_assignments(self, assignments):
        has_new_keys = assignments.has_new_keys
        changelog = assignments.consume_changelog()

        if has_new_keys:
            unknown_ids = set(changelog).difference(self._prioritizer.known)
            # We only want to update priorities, we'll decide who is assigned
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

            # The remaining case is True -> False, False -> True or
            # MISSING -> (True|False)

        # A very cheap sanity check
        ours = len(self._unassigned_pkg_ids)
        theirs = len(assignments) - assignments.num_assigned
        assert ours == theirs, "We failed to track variable assignments"


def LoggedPriorityInstalledFirstPolicty(pool, installed_repository):
    return PolicyLogger(PriorityQueuePolicy(pool, installed_repository))


def LoggedUndeterminedClausePolicy(pool, installed_repository):
    return PolicyLogger(UndeterminedClausePolicy(pool, installed_repository))

InstalledFirstPolicy = LoggedUndeterminedClausePolicy
