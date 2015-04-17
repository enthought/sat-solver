from simplesat.policy import InstalledFirstPolicy
from simplesat.pysolver_helpers import solver_from_rules_set, solve_sat
from simplesat.rules_generator import RulesGenerator
from simplesat.transaction import Transaction


class Solver(object):
    def __init__(self, pool, remote_repositories, installed_repository):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories

        self._sat_solver = None

    def solve(self, request):
        """Given an install request, provide a list of packages
        to be installed to resolve this request, or None if no
        resolution could be found.
        """
        solution = self._run_sat(request)

        installed_map = set(
            self._pool.package_id(p)
            for p in self._installed_repository.iter_packages()
        )

        return Transaction(self._pool, solution, installed_map)

    def _create_solver(self, request):

        pool = self._pool
        installed_repository = self._installed_repository

        policy = InstalledFirstPolicy(pool, installed_repository)

        assert len(request.jobs) == 1
        job = request.jobs[0]
        assert job.kind == 'install'
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

        rules_generator = RulesGenerator(pool, request)
        for package in installed_repository.iter_packages():
            rules_generator._add_installed_package_rules(package)

        rules = list(rules_generator.iter_rules())
        return solver_from_rules_set(rules, policy)

    def _run_sat(self, request):
        self._sat_solver = solver = self._create_solver(request)
        solution_ids = solve_sat(solver)
        return solution_ids
