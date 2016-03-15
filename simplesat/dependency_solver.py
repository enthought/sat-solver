import collections

import six

from simplesat.errors import NoPackageFound, SatisfiabilityError
from simplesat.pool import Pool
from simplesat.request import JobType, Request
from simplesat.rules_generator import RulesGenerator
from simplesat.sat.policy import InstalledFirstPolicy
from simplesat.sat import MiniSATSolver
from simplesat.transaction import Transaction
from simplesat.utils import timed_context, connected_nodes


def requirements_are_satisfiable(repositories, requirements):
    """ Return True if the requirements can be satisfied using the packages
    in the repositories, otherwise False. """
    request = Request()
    for requirement in requirements:
        request.install(requirement)
    pool = Pool(repositories)

    try:
        DependencySolver(pool, repositories, []).solve(request)
        return True
    except SatisfiabilityError:
        return False


class DependencySolver(object):

    def __init__(self, pool, remote_repositories, installed_repository,
                 policy=None, use_pruning=True, strict=False):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories
        self._last_rules_time = timed_context("Generate Rules")
        self._last_solver_init_time = timed_context("Solver Init")
        self._last_solve_time = timed_context("SAT Solve")

        self.strict = strict
        self.use_pruning = use_pruning

        self._policy = policy or InstalledFirstPolicy(
            pool, installed_repository
        )

    def solve(self, request):
        """Given a request, return a Transaction contianing the set of
        operations to apply to resolve it, or raise SatisfiabilityError
        if no resolution could be found.
        """
        with self._last_rules_time:
            requirement_ids, rules = self._create_rules_and_initialize_policy(
                request
            )
        with self._last_solver_init_time:
            sat_solver = MiniSATSolver.from_rules(rules, self._policy)
        with self._last_solve_time:
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

    def _create_rules_and_initialize_policy(self, request):
        pool = self._pool
        installed_repository = self._installed_repository

        all_requirement_ids = []

        for job in request.jobs:
            assert job.kind in (
                JobType.install, JobType.remove, JobType.update
            ), 'Unknown job kind: {}'.format(job.kind)

            requirement = job.requirement

            providers = tuple(pool.what_provides(requirement))
            if len(providers) == 0:
                raise NoPackageFound(requirement, str(requirement))

            if job.kind == JobType.update:
                # An update request *must* install the latest package version
                def key(package):
                    return (package.version, package in installed_repository)
                providers = [max(providers, key=key)]

            requirement_ids = [pool.package_id(p) for p in providers]
            self._policy.add_requirements(requirement_ids)
            all_requirement_ids.extend(requirement_ids)

        installed_map = collections.OrderedDict()
        for package in installed_repository:
            installed_map[pool.package_id(package)] = package

        rules_generator = RulesGenerator(
            pool, request, installed_map=installed_map, strict=self.strict)

        return all_requirement_ids, list(rules_generator.iter_rules())


def _connected_packages(solution, root_ids, pool):
    """ Return packages in `solution` which are associated with `root_ids`. """

    # Our strategy is as follows:
    # ... -> pkg.install_requires -> pkg names -> ids -> _id_to_package -> ...

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

    # FIXME: can use package_lit_dependency_graph() here
    def neighborfunc(pkg_id):
        """ Given a pkg id, return the pkg ids of the immediate dependencies
        that appeared in our solution. """
        constraints = pool._id_to_package[pkg_id].install_requires
        neighbors = set(solution_name_to_id[name] for name, _ in constraints)
        return neighbors

    # Each package can root its own independent graph, so we must start at
    # each one individually
    should_include = set()
    for pkg_id in solution_root_ids:
        # We pass in `should_include` to avoid re-walking a subgraph
        nodes = connected_nodes(pkg_id, neighborfunc, should_include)
        should_include.update(nodes)
    assert should_include.issuperset(solution_root_ids)

    # In addition to all updates and additions to root ids, we must also keep
    # all packages newly *excluded* from root_ids
    connected = should_include.union(s for s in solution if abs(s) in root_ids)
    return connected


def _solution_to_ids(solution):
    # Return solution as list of signed integers.
    ids = (pkg_id if value else -pkg_id
           for pkg_id, value in six.iteritems(solution))
    return sorted(ids, key=lambda lit: abs(lit))
