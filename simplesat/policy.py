from __future__ import absolute_import

from collections import defaultdict, OrderedDict

from enstaller.collections import DefaultOrderedDict


class InstalledFirstPolicy(object):

    def __init__(self, pool):
        self._pool = pool
        self._decision_set = set()

    def add_packages_by_id(self, package_ids):
        # TODO Just make this add_requirement.
        for package_id in package_ids:
            self._decision_set.add(package_id)

    def get_next_package_id(self, assignments, clauses):
        """Get the next unassigned package.
        """

        decision_set = self._decision_set
        if len(decision_set) == 0:
            # TODO inefficient and verbose
            unassigned_ids = set(
                literal for literal, status in assignments.iteritems()
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
                if signed_assignments.intersection(clause.lits):
                    # Clause is true
                    continue

                literals = clause.lits
                undecided = unassigned_ids.intersection(literals)

                decision_set.update(abs(lit) for lit in undecided)

            if len(decision_set) == 0:
                # This will happen if the remaining packages are irrelevant for
                # the set of rules that we're trying to satisfy. In that case,
                # just return one of the undecided IDs.

                # We use min to ensure determinisism
                return -min(unassigned_ids)

        # Sort packages by name
        packages_by_name = DefaultOrderedDict(list)
        for package_id in decision_set:
            package = self._pool._id_to_package[package_id]
            packages_by_name[package.name].append(package)

        # Get the highest version of the first package that we encounter.
        candidate_name = packages_by_name.keys()[0]
        candidate_packages = packages_by_name[candidate_name]
        max_version = max(candidate_packages,
                          key=lambda package: package.version)

        max_version_id = self._pool.package_id(max_version)

        assert assignments[max_version_id] is None, \
            "Trying to assign to a variable which is already assigned."

        # Clear out decision set.
        self._decision_set = set()
        return self._pool.package_id(max_version)
