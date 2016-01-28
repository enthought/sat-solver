#!/usr/bin/env python
# -*- coding: utf-8 -*-

import six

from simplesat.utils import DefaultOrderedDict
from .policy import IPolicy, pkg_id_to_version
from .policy_logger import PolicyLogger


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

        assert assignments.get(candidate_id) is None, \
            "Trying to assign to a variable which is already assigned."

        if not self.prefer_installed:
            # If this exact package version is available locally, use that one
            key = self._package_key(candidate_id)
            candidate_id = self._preferred_package_ids.get(key, candidate_id)

        return candidate_id

    def _without_assigned(self, package_ids, assignments):
        return set(
            pkg_id for pkg_id in package_ids
            if assignments.get(pkg_id) is None
        )

    def _best_candidate(self, package_ids, assignments):
        by_version = six.functools.partial(pkg_id_to_version, self._pool)
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
