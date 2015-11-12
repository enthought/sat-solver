import collections

import six

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
        """Given a request, return a Transaction contianing the set of
        operations to apply to resolve it, or raise SatisfiabilityError
        if no resolution could be found.
        """
        requirement_ids, rules = self._create_rules(request)
        sat_solver = MiniSATSolver.from_rules(rules, self._policy)
        solution = sat_solver.search()

        solution_ids = _solution_to_ids(solution)

        installed_map = set(
            self._pool.package_id(p)
            for p in self._installed_repository
        )

        if self.use_pruning:
            root_ids = installed_map.union(requirement_ids)
            solution_ids = _connected_packages(
                solution_ids, root_ids, self._pool
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


def _connected_packages(solution, root_ids, pool):
    """ Return packages in `solution` which are associated with `root_ids`. """

    # Our strategy is as follows:
    # ... -> pkg.dependencies -> pkg strings -> ids -> _id_to_package -> ...

    def get_name(pkg_id):
        return pool._id_to_package[abs(pkg_id)].name

    root_names = {get_name(pkg_id) for pkg_id in root_ids}

    solution_name_to_id = {
        get_name(pkg_id): pkg_id for pkg_id in solution
        if pkg_id > 0
    }

    solution_root_ids = set(
        pkg_id for name, pkg_id in six.iteritems(solution_name_to_id)
        if name in root_names
    )

    def neighborfunc(pkg_id):
        """ Given a pkg id, return the pkg ids of the immediate dependencies
        that appeared in our solution. """
        dep_strings = pool._id_to_package[pkg_id].dependencies
        pkg_names = (
            Requirement.from_legacy_requirement_string(d).name
            for d in dep_strings
        )
        neighbors = set(solution_name_to_id[name] for name in pkg_names)
        return neighbors

    # Each package can root its own independent graph, so we must start at
    # each one individually
    should_include = set()
    for pkg_id in solution_root_ids:
        # We pass in `should_keep` to avoid re-walking a subgraph
        nodes = _connected_nodes(pkg_id, neighborfunc, should_include)
        should_include.update(nodes)
    assert should_include.issuperset(solution_root_ids)

    # In addition to all updates and additions to root ids, we must also keep
    # all packages newly *excluded* from root_ids
    connected = should_include.union(s for s in solution if abs(s) in root_ids)
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
    ids = (pkg_id if value else -pkg_id
           for pkg_id, value in six.iteritems(solution))
    return sorted(ids, key=lambda lit: abs(lit))
