import collections

from enstaller.solver import JobType

from simplesat.sat.policy import InstalledFirstPolicy
from simplesat.sat import MiniSATSolver
from simplesat.rules_generator import RulesGenerator
from simplesat.transaction import Transaction


class DependencySolver(object):
    def __init__(self, pool, remote_repositories, installed_repository,
                 policy=None):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories

        self._policy = policy or InstalledFirstPolicy(
            pool, installed_repository
        )

    def solve(self, request):
        """Given a request, computes the set of operations to apply to
        resolve it, or None if no resolution could be found.
        """
        rules = self._create_rules(request)
        sat_solver = MiniSATSolver.from_rules(rules, self._policy)
        solution = sat_solver.search()

        if solution is False:
            return None
        else:
            solution_ids = _solution_to_ids(solution)

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

        return list(rules_generator.iter_rules())


def _solution_to_ids(solution):
    # Return solution as list of signed integers.
    return sorted(
        [(+1 if value else -1) * _id for _id, value in solution.items()],
        key=lambda lit: abs(lit)
    )
