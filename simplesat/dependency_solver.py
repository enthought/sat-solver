import collections

from egginst.errors import NoPackageFound
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
        if len(requirement_ids) == 0:
            raise NoPackageFound(str(requirement), requirement)
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


def _connected_packages(solution, pkg_ids, pool):
    """ Return all packages in solution that might be installed,
    removed, or updated due to a change in any of the packages in `pkg_ids`.
    """

    # Our strategy is as follows:
    # .. -> pkg deps + conflicts -> pkg strings -> ids -> _id_to_package -> ..

    pkg_name_to_ids = collections.defaultdict(set)
    # Signed literals as in `solution`, e.g. {'numpy': {-4, 5, 7, 22}}
    for pkg_id in solution:
        pkg = pool._id_to_package[abs(pkg_id)]
        pkg_key = pkg.name
        pkg_name_to_ids[pkg_key].add(pkg_id)

    def neighborfunc(pkg_id):
        """ Given a pkg id, return the pkg ids of the dependencies that
        appeared in our solution. """

        # Only installed packages can pull in other packages
        if pkg_id < 0:
            return set()

        pkg = pool._id_to_package[pkg_id]

        dep_pkg_strings = pkg.dependencies
        dep_pkg_names = (
            Requirement.from_legacy_requirement_string(d).name
            for d in dep_pkg_strings
        )
        neighbors = pkg_name_to_ids[pkg.name].copy()
        neighbors.update(
            neighbor
            for name in dep_pkg_names
            for neighbor in pkg_name_to_ids[name]
        )
        neighbors.remove(pkg_id)
        return neighbors

    # Each package can root its own independent graph, so we must start at
    # each one individually
    connected = set()
    for pkg_id in set(pkg_ids).intersection(solution):
        if pkg_id < 0:
            continue
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
