#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

import six

from simplesat.utils import DefaultOrderedDict
from .policy import IPolicy, pkg_id_to_version
from .policy_logger import LoggedPolicy


class UndeterminedClausePolicy(IPolicy):

    """ An IPolicy that gathers all undetermined packages from clauses whose
    truth value is not yet known and suggests them in descending order by
    package version number. """

    def __init__(self, pool, installed_repository, prefer_installed=True):
        self._pool = pool
        self.prefer_installed = prefer_installed
        by_version = six.functools.partial(pkg_id_to_version, self._pool)
        self._installed_ids = sorted(
            (pool.package_id(package) for package in installed_repository),
            key=by_version
        )
        self._preferred_package_ids = {
            self._package_key(package_id): package_id
            for package_id in self._installed_ids
        }
        self._decision_set = set()
        self._requirements = set()
        self._unsatisfied_clauses = set()
        self._id_to_clauses = defaultdict(list)
        self._all_ids = set()

    def _package_key(self, package_id):
        package = self._pool.id_to_package(package_id)
        return (package.name, package.version)

    def add_requirements(self, package_ids):
        self._requirements.update(package_ids)

    def _update_cache_from_assignments(self, assignments):
        changelog = assignments.consume_changelog()
        for key in six.iterkeys(changelog):
            for clause in self._id_to_clauses[key]:
                if any(assignments.value(l) for l in clause.lits):
                    self._unsatisfied_clauses.discard(clause)
                else:
                    self._unsatisfied_clauses.add(clause)

    def _build_id_to_clauses(self, clauses):
        """ Return a mapping from package ids to a list of clauses containing
        that id.
        """
        table = defaultdict(list)
        for c in clauses:
            for l in c.lits:
                table[abs(l)].append(c)
        self._all_ids = set(six.iterkeys(table))
        return dict(table)

    def get_next_package_id(self, assignments, clauses):
        """Get the next unassigned package.
        """
        if assignments.new_keys:
            self._id_to_clauses = self._build_id_to_clauses(clauses)
            self._refresh_decision_set(assignments)
        candidate_id = None
        best = self._best_candidate

        if self.prefer_installed:
            candidate_id = self._best_sorted_candidate(
                self._installed_ids, assignments)

        if candidate_id is None:
            candidate_id = best(self._requirements, assignments)

        if candidate_id is None:
            candidate_id = best(self._decision_set, assignments, update=True)

        if candidate_id is None:
            self._refresh_decision_set(assignments)
            candidate_id = best(self._decision_set, assignments)
            if candidate_id is None:
                candidate_id = best(self._all_ids, assignments)

        assert assignments.get(candidate_id) is None, \
            "Trying to assign to a variable which is already assigned."

        if not self.prefer_installed:
            # If this exact package version is available locally, use it.
            # NOTE: when repository priority is implemented, this will cause
            # the virtual <installed> repository to act as if it always has the
            # highest priority.
            key = self._package_key(candidate_id)
            candidate_id = self._preferred_package_ids.get(key, candidate_id)

        return candidate_id

    def _without_assigned(self, package_ids, assignments):
        return package_ids.difference(assignments.assigned_ids)

    def _best_sorted_candidate(self, package_ids, assignments):
        for p_id in package_ids:
            if p_id not in assignments.assigned_ids:
                return p_id

    def _best_candidate(self, package_ids, assignments, update=False):
        by_version = six.functools.partial(pkg_id_to_version, self._pool)
        unassigned = self._without_assigned(package_ids, assignments)
        if update:
            package_ids.clear()
            package_ids.update(unassigned)
        try:
            return max(unassigned, key=by_version)
        except ValueError:
            return None

    def _group_packages_by_name(self, decision_set):
        installed_packages = []
        new_package_map = DefaultOrderedDict(list)
        installed_ids = set(self._installed_ids)

        for package_id in sorted(decision_set):
            package = self._pool.id_to_package(package_id)
            if package_id in installed_ids:
                installed_packages.append(package)
            else:
                new_package_map[package.name].append(package)

        return installed_packages, new_package_map

    def _refresh_decision_set(self, assignments):
        self._update_cache_from_assignments(assignments)
        self._decision_set.clear()
        self._decision_set.update(
            abs(lit)
            for clause in self._unsatisfied_clauses
            for lit in clause.lits
        )
        self._decision_set.difference_update(assignments.assigned_ids)


LoggedUndeterminedClausePolicy = LoggedPolicy(UndeterminedClausePolicy)
