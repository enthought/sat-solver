from collections import OrderedDict

from attr import attr, attributes

from .constraints import Requirement
from simplesat.utils.graph import toposort, package_lit_dependency_graph


@attributes
class Operation(object):
    package = attr()


@attributes
class UpdateOperation(Operation):
    source = attr()


@attributes
class InstallOperation(Operation):
    pass


@attributes
class RemoveOperation(Operation):
    pass


class Transaction(object):

    def __init__(self, pool, decisions, installed_map, modifiers):
        self.modifiers = modifiers
        self.operations = self._safe_operations(
            pool, decisions, installed_map)
        self.pretty_operations = self._as_pretty_operations(
            pool, self.operations)

    def __iter__(self):
        return iter(self.operations)

    def __str__(self):
        return self.to_string(self.operations)

    @staticmethod
    def to_string(operations):
        lines = []
        for operation in operations:
            if isinstance(operation, InstallOperation):
                lines.append("Installing:\n\t{}".format(operation.package))
            elif isinstance(operation, UpdateOperation):
                lines.append(
                    "Updating:\n\t{}\n\t{}".format(operation.source,
                                                   operation.package)
                )
            elif isinstance(operation, RemoveOperation):
                lines.append("Removing\n\t{}".format(operation.package))
            else:
                msg = "Unknown operation: {!r}".format(operation)
                raise ValueError(msg)

        return "\n".join(lines)

    def to_simple_string(self):
        S = "{0.name} ({0.version})".format
        lines = []
        for operation in self.operations:
            if isinstance(operation, InstallOperation):
                lines.append("Installing {}".format(S(operation.package)))
            elif isinstance(operation, UpdateOperation):
                lines.append(
                    "Updating {} to {}".format(S(operation.source),
                                               S(operation.package))
                )
            elif isinstance(operation, RemoveOperation):
                lines.append("Removing {}".format(S(operation.package)))
            else:
                msg = "Unknown operation: {!r}".format(operation)
                raise ValueError(msg)

        return "\n".join(lines)

    def _as_pretty_operations(self, pool, operations):
        pkg_to_ops = OrderedDict((op.package, [op]) for op in operations)

        for pkg in reversed(tuple(pkg_to_ops.keys())):
            if pkg in pkg_to_ops:
                for update in self._find_other_providers(pool, pkg):
                    pkg_to_ops[pkg] += pkg_to_ops.pop(update, [])

        combine = self._merge_operations
        return [combine(ops) for ops in pkg_to_ops.values()]

    def _merge_operations(self, ops):
        if len(ops) == 1:
            return ops[0]
        rank = (InstallOperation, RemoveOperation)
        first, second = sorted(ops, key=lambda o: rank.index(o.__class__))
        return UpdateOperation(first.package, second.package)

    def _safe_operations(self, pool, decisions, installed_map):
        graph = package_lit_dependency_graph(
            pool, decisions, closed=True, modifiers=self.modifiers)
        removals = []
        installs = []
        operations = []

        # This builds from the bottom (no dependencies) up
        for group in toposort(graph):
            # Sort the set of independent packages for determinism
            for package_id in sorted(group, key=abs):
                assert package_id in decisions
                if package_id < 0 and -package_id in installed_map:
                    removals.append(-package_id)
                elif package_id > 0 and package_id not in installed_map:
                    installs.append(package_id)

        # Removals should happen top down
        for package_id in reversed(removals):
            package = pool._id_to_package[package_id]
            operations.append(RemoveOperation(package))

        # Installations should happen bottom up
        for package_id in installs:
            package = pool._id_to_package[package_id]
            operations.append(InstallOperation(package))

        return operations

    def _find_other_providers(self, pool, package):
        # NOTE: this assumes that the name of the package is also the name of
        # the thing that is being provided. This is not always true. Consider
        # that apache2 and nginx can both provide "webserver", etc.
        requirement = Requirement._from_string(package.name)
        return [
            p for p in pool.what_provides(requirement) if p != package
        ]
