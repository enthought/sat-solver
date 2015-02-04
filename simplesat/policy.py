# Simple policy class.
from collections import defaultdict


class InstalledFirstPolicy(object):

    def __init__(self, pool, installed_ids, requirement):
        self._pool = pool
        self._installed_ids = installed_ids
        self._requirement = requirement

    def get_next_variable(self, assignments):
        # Given a dictionary of partial assignments, get an undecided variable
        # to be decided next.

        # Composer maintains a separate queue and pushes these packages onto
        # the queue at the beginning of running the solver.
        preferred = self._pool.what_provides(self._requirement)
        preferred.sort(key=lambda package: package.version, reverse=True)

        preferred_ids = [self._pool.package_id(package)
                         for package in preferred]
        installed_ids = [
            package_id for package_id, status in assignments.iteritems()
            if status
        ]
        if set(preferred_ids) & set(installed_ids):
            # We've already installed the requirement, continue with
            # dependencies.
            pass
        else:
            print "Suggesting", preferred[0]
            return preferred_ids[0]

        undecided = [
            package_id for package_id, status in assignments.iteritems()
            if status is None
        ]
        installed_packages, new_package_map = \
            self._group_packages_by_name(undecided)

        if len(installed_packages) > 0:
            candidate = installed_packages[0]
        else:
            for new_versions in new_package_map.values():
                new_versions.sort(
                    key=lambda package: package.version, reverse=True)
                candidate = new_versions[0]
                break
            else:
                # This should not happen.
                raise ValueError()
                candidate = None

        return self._pool.package_id(candidate)

    def _group_packages_by_name(self, undecided):
        installed_packages = []
        new_package_map = defaultdict(list)

        for package_id in undecided:
            package = self._pool._id_to_package[package_id]
            if package_id in self._installed_ids:
                installed_packages.append(package)
            else:
                new_package_map[package.name].append(package)

        return installed_packages, new_package_map
