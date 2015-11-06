from collections import OrderedDict

from enstaller.new_solver import Requirement


class Operation(object):
    def __init__(self, package):
        self.package = package


class UpdateOperation(Operation):
    def __init__(self, package, source):
        super(UpdateOperation, self).__init__(package)
        self.source = source


class InstallOperation(Operation):
    pass


class RemoveOperation(Operation):
    pass


class FailureOperation(Operation):
    def __init__(self, reason):
        super(FailureOperation, self).__init__(None)
        self.reason = reason


class Transaction(object):

    @classmethod
    def failure(self, reason, pool=None, decisions=None, installed_map=None):
        decisions = [] if decisions is None else decisions
        installed_map = set() if installed_map is None else installed_map
        transaction = Transaction(pool, decisions, installed_map)
        transaction.fail(reason)
        return transaction

    def __init__(self, pool, decisions, installed_map):
        self.operations = []

        self._compute_transaction(pool, decisions, installed_map)

    def __iter__(self):
        return iter(self.operations)

    def __str__(self):
        lines = []
        for operation in self.operations:
            if isinstance(operation, InstallOperation):
                lines.append("Installing:\n\t{}".format(operation.package))
            elif isinstance(operation, UpdateOperation):
                lines.append(
                    "Updating:\n\t{}\n\t{}".format(operation.source,
                                                   operation.package)
                )
            elif isinstance(operation, RemoveOperation):
                lines.append("Removing {}".format(operation.package))
            elif isinstance(operation, FailureOperation):
                lines.append("Failure: {}".format(operation.reason))
            else:
                msg = "Unknown operation: {!r}".format(operation)
                raise ValueError(msg)

        return "\n".join(lines)

    def _compute_transaction(self, pool, decisions, installed_map):
        installed_means_update_map = \
            self._compute_means_update_map(pool, decisions, installed_map)

        update_map = OrderedDict()
        install_map = OrderedDict()
        remove_map = OrderedDict()

        ignored_remove = set()

        for decision in sorted(decisions):
            package_id = abs(decision)
            package = pool._id_to_package[package_id]

            if decision > 0 and package_id in installed_map:
                continue

            if decision < 0 and package_id not in installed_map:
                continue

            if decision > 0:
                if package_id in installed_means_update_map:
                    source = installed_means_update_map.pop(package_id)
                    update_map[package_id] = UpdateOperation(package, source)
                    ignored_remove.add(pool._package_to_id[source])
                else:
                    install_map[package_id] = Operation(package)

        for decision in sorted(decisions):
            package_id = abs(decision)
            package = pool._id_to_package[package_id]

            if decision < 0 and package_id in installed_map:
                if package_id not in ignored_remove:
                    remove_map[package_id] = Operation(package)

        return self._compute_transaction_from_maps(pool, install_map,
                                                   update_map, remove_map)

    def install(self, package):
        self._check_failed()
        self.operations.append(InstallOperation(package))

    def remove(self, package):
        self._check_failed()
        self.operations.append(RemoveOperation(package))

    def update(self, from_package, to_package):
        self._check_failed()
        self.operations.append(UpdateOperation(to_package, from_package))

    def fail(self, reason):
        if self.operations:
            msg = "Failure not permitted after other operations"
            raise ValueError(msg)
        self.operations.append(FailureOperation(reason))

    @property
    def failed(self):
        ops = self.operations
        return len(ops) > 0 and isinstance(ops[0], FailureOperation)

    def _check_failed(self):
        if self.failed:
            msg = "Operations not permitted after failure"
            raise ValueError(msg)

    def _find_updates(self, pool, package):
        requirement = Requirement._from_string(package.name)
        return [p for p in pool.what_provides(requirement)
                if p.version > package.version]

    def _compute_means_update_map(self, pool, decisions, installed_map):
        means_update_map = OrderedDict()

        for decision in sorted(decisions):
            package_id = abs(decision)
            package = pool._id_to_package[package_id]

            if decision < 0 and package_id in installed_map:
                for update_package in self._find_updates(pool, package):
                    update_package_id = pool.package_id(update_package)
                    means_update_map[update_package_id] = package

        return means_update_map

    def _compute_transaction_from_maps(self, pool, install_map, update_map,
                                       remove_map):
        operations = self._compute_root_packages(pool, install_map, update_map)
        queue = [operation.package for operation in operations.values()]

        visited_ids = set()

        # Install/update packages, starting from the ones which do not
        # depend on anything else (using topological sort)
        # FIXME: better implementation
        while len(queue) > 0:
            package = queue.pop()
            package_id = pool.package_id(package)

            if package_id in visited_ids:
                if package_id in install_map:
                    operation = install_map.pop(package_id)
                    self.install(operation.package)
                if package_id in update_map:
                    operation = update_map.pop(package_id)
                    self.update(operation.source, operation.package)
            else:
                queue.append(package)
                # We use sorted for determinism
                for dependency in sorted(package.dependencies):
                    package_requirement = \
                        Requirement.from_legacy_requirement_string(dependency)
                    candidates = pool.what_provides(package_requirement)
                    queue.extend(candidates)

                visited_ids.add(package_id)

        for operation in remove_map.values():
            self.remove(operation.package)

    def _compute_root_packages(self, pool, install_map, update_map):
        """ Look at the root packages in the given maps.

        Root packages are packages which are not dependencies of other
        packages.
        """
        packages = OrderedDict(install_map)
        packages.update(update_map)

        roots = packages.copy()

        for package_id, operation in packages.items():
            package = operation.package

            if package_id not in roots:
                continue

            for dependency in package.dependencies:
                candidates = pool.what_provides(
                    Requirement.from_legacy_requirement_string(dependency)
                )
                for candidate in candidates:
                    candidate_id = pool.package_id(candidate)
                    roots.pop(candidate_id, None)

        return roots
