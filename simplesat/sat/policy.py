import abc

import six

from enstaller.collections import DefaultOrderedDict


class IPolicy(six.with_metaclass(abc.ABCMeta)):
    @abc.abstractmethod
    def get_next_package_id(self, assignments, clauses):
        """ Returns a undecided variable (i.e. integer > 0) for the given sets
        of assignements and clauses.
        """


class DefaultPolicy(IPolicy):
    def get_next_package_id(self, assignments, _):
        # Given a dictionary of partial assignments, get an undecided variable
        # to be decided next.
        undecided = [
            package_id for package_id, status in six.iteritems(assignments)
            if status is None
        ]
        return undecided[0]


class InstalledFirstPolicy(IPolicy):
    def __init__(self, pool, installed_repository):
        self._pool = pool
        self._decision_set = set()
        self._installed_map = set(
            pool.package_id(package) for package in
            installed_repository.iter_packages()
        )

    def add_packages_by_id(self, package_ids):
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
