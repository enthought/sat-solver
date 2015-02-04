# Simple policy class.
from collections import defaultdict


class InstalledFirstPolicy(object):

    def __init__(self, pool, installed_ids):
        self._pool = pool
        self._installed_ids = installed_ids

    def get_next_variable(self, assignments):
        # Given a dictionary of partial assignments, get an undecided variable
        # to be decided next.
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
