import abc
from collections import Counter

import six

from enstaller.collections import DefaultOrderedDict


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

    def __init__(self, policy, extra_args=None, extra_kwargs=None):
        self._policy = policy
        self._log_pool = policy._pool
        self._log_installed = policy._installed_ids.copy()
        self._log_preferred = getattr(policy, '_preferred_ids', set()).copy()
        self._log_extra_args = extra_args
        self._log_extra_kwargs = extra_kwargs
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
        if self._log_assignment_changes:
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
        undecided = (
            package_id for package_id, status in six.iteritems(assignments)
            if status is None
        )
        return next(undecided)


class UndeterminedClausePolicy(IPolicy):

    """ An IPolicy that gathers all undetermined packages from clauses whose
    truth value is not yet known and suggests them in descending order by
    package version number. """

    def __init__(self, pool, installed_repository, prefer_installed=True):
        self._pool = pool
        self.prefer_installed = prefer_installed
        self._installed_ids = set(
            pool.package_id(package) for package in installed_repository
        )
        self._preferred_package_ids = {
            self._package_key(package_id): package_id
            for package_id in self._installed_ids
        }
        self._decision_set = set()
        self._requirements = set()

    def _package_key(self, package_id):
        package = self._pool._id_to_package[package_id]
        return (package.name, package.version)

    def add_requirements(self, package_ids):
        self._requirements.update(package_ids)

    def get_next_package_id(self, assignments, clauses):
        """Get the next unassigned package.
        """
        candidate_id = None
        best = self._best_candidate

        if self.prefer_installed:
            candidate_id = best(self._installed_ids, assignments)

        candidate_id = (
            candidate_id or
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

        assert assignments.value(candidate_id) is None, \
            "Trying to assign to a variable which is already assigned."

        if not self.prefer_installed:
            # If this exact package version is available locally, use that one
            key = self._package_key(candidate_id)
            candidate_id = self._preferred_package_ids.get(key, candidate_id)

        return candidate_id

    def _without_assigned(self, package_ids, assignments):
        return set(
            pkg_id for pkg_id in package_ids
            if assignments.value(pkg_id) is None
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


def LoggedUndeterminedClausePolicy(pool, installed_repository,
                                   *args, **kwargs):
    policy = UndeterminedClausePolicy(
        pool, installed_repository, *args, **kwargs
    )
    logger = PolicyLogger(policy, extra_args=args, extra_kwargs=kwargs)
    return logger

InstalledFirstPolicy = LoggedUndeterminedClausePolicy
