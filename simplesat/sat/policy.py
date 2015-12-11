import abc
from collections import Counter

import six

from enstaller.collections import DefaultOrderedDict


class IPolicy(six.with_metaclass(abc.ABCMeta)):

    @abc.abstractmethod
    def add_requirements(self, package_ids):
        """ Submit packages to the policy for consideration.
        """

    @abc.abstractmethod
    def get_next_package_id(self, assignments, clauses):
        """ Returns a undecided variable (i.e. integer > 0) for the given sets
        of assignements and clauses.
        """


class PolicyLogger(IPolicy):

    def __init__(self, policy):
        self._policy = policy
        self._log_pool = policy._pool
        self._log_installed = policy._installed_ids.copy()
        self._log_preferred = getattr(policy, '_preferred_ids', set()).copy()
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
        self._log_preferred.difference_update(package_ids)
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
        try:
            repo = package.repository_info.name
        except AttributeError:
            repo = ''
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
        preferred = set(self._log_preferred)
        installed = set(self._log_installed)
        for (i, sugg) in enumerate(ids):
            pretty = self._log_pretty_pkg_id(sugg)
            R = 'R' if sugg in required else ' '
            P = 'P' if sugg in preferred else ' '
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
                    changes = '\n\t\t'.join([''] + changes)
                else:
                    changes = ""
            except IndexError:
                changes = ""
            msg = "{:>4} {}{}{} - {}{}"
            report.append(msg.format(i, R, P, I, pretty, changes))
        return '\n'.join(report)


class DefaultPolicy(IPolicy):

    def add_requirements(self, assignments):
        pass

    def get_next_package_id(self, assignments, _):
        # Given a dictionary of partial assignments, get an undecided variable
        # to be decided next.
        undecided = [
            package_id for package_id, status in six.iteritems(assignments)
            if status is None
        ]
        return undecided[0]


class UndeterminedClausePolicy(IPolicy):

    """ An IPolicy that gathers all undetermined packages from clauses whose
    truth value is not yet known and suggests them in descending order by
    package version number. """

    def __init__(self, pool, installed_repository):
        self._pool = pool
        self._decision_set = set()
        self._installed_ids = set(
            pool.package_id(package) for package in installed_repository
        )

    def add_requirements(self, package_ids):
        self._decision_set.update(package_ids)

    def get_next_package_id(self, assignments, clauses):
        """Get the next unassigned package.
        """

        self._decision_set.update(self._installed_ids)
        decision_set = self._decision_set
        # Remove everything that is currently assigned
        if len(decision_set) > 0:
            decision_set.difference_update(
                a for a, v in six.iteritems(assignments)
                if v is not None
            )
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

        return candidate_id

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

            literals = clause.lits
            undecided = unassigned_ids.intersection(literals)

            self._decision_set.update(abs(lit) for lit in undecided)

        if len(self._decision_set) == 0:
            # This will happen if the remaining packages are irrelevant for
            # the set of rules that we're trying to satisfy. In that case,
            # just return one of the undecided IDs.

            # We use min to ensure determinisism
            return self._decision_set, -min(unassigned_ids)
        else:
            return self._decision_set, None


def LoggedUndeterminedClausePolicy(pool, installed_repository):
    return PolicyLogger(UndeterminedClausePolicy(pool, installed_repository))

InstalledFirstPolicy = LoggedUndeterminedClausePolicy
