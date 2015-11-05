import collections

from enstaller.solver import JobType
from enstaller.new_solver import Requirement

from simplesat.sat.policy import InstalledFirstPolicy
from simplesat.sat import MiniSATSolver
from simplesat.rules_generator import RulesGenerator
from simplesat.transaction import Transaction


class DependencySolver(object):
    def __init__(self, pool, remote_repositories, installed_repository,
                 policy=None, use_pruning=True):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories
        self.use_pruning = use_pruning

        self._policy = policy or InstalledFirstPolicy(
            pool, installed_repository
        )

    def solve(self, request):
        """Given a request, computes the set of operations to apply to
        resolve it, or None if no resolution could be found.
        """
        requirement_ids, rules = self._create_rules(request)
        sat_solver = MiniSATSolver.from_rules(rules, self._policy)
        solution = sat_solver.search()

        if solution is False:
            return None
        else:
            solution_ids = _solution_to_ids(solution)

            if self.use_pruning:
                connected = _connected_packages(
                    solution_ids, requirement_ids, self._pool)
                solution_ids = [i for i in solution_ids if i in connected]

            installed_map = set(
                self._pool.package_id(p)
                for p in self._installed_repository.iter_packages()
            )

            return Transaction(self._pool, solution_ids, installed_map)

    def _create_rules(self, request):
        pool = self._pool
        installed_repository = self._installed_repository

        assert len(request.jobs) == 1
        job = request.jobs[0]
        assert job.kind in (JobType.install, JobType.remove)
        requirement = job.requirement

        requirement_ids = [
            pool.package_id(package)
            for package in pool.what_provides(requirement)
        ]
        self._policy.add_packages_by_id(requirement_ids)

        # Add installed packages.
        self._policy.add_packages_by_id(
            [pool.package_id(package) for package in installed_repository]
        )

        installed_map = collections.OrderedDict()
        for package in installed_repository:
            installed_map[pool.package_id(package)] = package

        rules_generator = RulesGenerator(pool, request, installed_map)

        return requirement_ids, list(rules_generator.iter_rules())


def _connected_packages(solution, requirement_ids, pool):
    """ Return packages which are associated with a requirement. """

    # Our strategy is as follows:
    # ... -> pkg.dependencies -> pkg strings -> ids -> _id_to_package -> ...

    # We only need to identify packages which will be installed
    sol_set = set(s for s in solution if s > 0)

    # This dict can recover ids from the strings produced by pkg.dependencies
    package_string_to_id = {}
    for pkg_id in sol_set:
        pkg = pool._id_to_package[pkg_id]
        pkg_key = pkg.name
        package_string_to_id[pkg_key] = pkg_id

    def neighborfunc(pkg_id):
        """ Given a pkg id, return the pkg ids of the dependencies that
        appeared in our solution. """
        dep_strings = pool._id_to_package[pkg_id].dependencies
        pkg_keys = (
            Requirement.from_legacy_requirement_string(d).name
            for d in dep_strings
        )
        neighbors = set(package_string_to_id[key] for key in pkg_keys)
        return neighbors

    # A requirement can root its own independent graph, so we must start at
    # each one individually
    connected = set()
    for pkg_id in requirement_ids:
        # We pass in `connected` to avoid re-walking a graph we've seen before
        connected.update(_connected_nodes(pkg_id, neighborfunc, connected))

    return connected


def _connected_nodes(node, neighborfunc, visited):
    """ Recursively build up a set of nodes connected to `node` by following
    neighbors as given by `neighborfunc(node)`. """
    visited.add(node)
    queued = set([node])

    while queued:
        node = queued.pop()
        visited.add(node)
        neighbors = neighborfunc(node)
        queued.update(neighbors)
        queued.difference_update(visited)

    return visited


def _solution_to_ids(solution):
    # Return solution as list of signed integers.
    return sorted(
        ((+1 if value else -1) * _id for _id, value in solution.items()),
        key=lambda lit: abs(lit)
    )
