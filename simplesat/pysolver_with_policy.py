import collections

from enstaller.solver import JobType

from simplesat.policy import InstalledFirstPolicy
from simplesat.pysolver_helpers import solver_from_rules_set, solve_sat
from simplesat.rules_generator import RulesGenerator
from simplesat.transaction import Transaction


class Solver(object):
    def __init__(self, pool, remote_repositories, installed_repository):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories

    def solve(self, request):
        """Given a request, computes the set of operations to apply to
        resolve it, or None if no resolution could be found.
        """
        rules, policy = self._create_rules_and_policy(request)
        sat_solver = solver_from_rules_set(rules, policy)
        solution_ids = solve_sat(sat_solver)

        installed_map = set(
            self._pool.package_id(p)
            for p in self._installed_repository.iter_packages()
        )

        return Transaction(self._pool, solution_ids, installed_map)

    def _create_rules_and_policy(self, request):

        pool = self._pool
        installed_repository = self._installed_repository

        policy = InstalledFirstPolicy(pool, installed_repository)

        assert len(request.jobs) == 1
        job = request.jobs[0]
        assert job.kind in (JobType.install, JobType.remove)
        requirement = job.requirement

        requirement_ids = [
            pool.package_id(package)
            for package in pool.what_provides(requirement)
        ]
        policy.add_packages_by_id(requirement_ids)

        # Add installed packages.
        policy.add_packages_by_id(
            [pool.package_id(package)
             for package in installed_repository.iter_packages()]
        )

        installed_map = collections.OrderedDict()
        for package in installed_repository:
            installed_map[pool.package_id(package)] = package

        rules_generator = RulesGenerator(pool, request, installed_map)

        return list(rules_generator.iter_rules()), policy
