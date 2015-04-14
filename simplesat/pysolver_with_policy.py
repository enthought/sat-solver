from simplesat.policy import InstalledFirstPolicy
from simplesat.pysolver_helpers import solver_from_rules_set, solve_sat
from simplesat.rules_generator import RulesGenerator


def resolve_request(pool, request, installed_repository):
    """Given an install request, provide a list of packages
    to be installed to resolve this request, or None if no
    resolution could be found.

    """
    policy = InstalledFirstPolicy(pool, installed_repository)

    assert len(request.jobs) == 1
    job = request.jobs[0]
    assert job.kind == 'install'
    requirement = job.requirement

    requirement_ids = [
        pool.package_id(package) for package in pool.what_provides(requirement)
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
    solv = solver_from_rules_set(rules, policy)
    solution_ids = solve_sat(solv)
    return solution_ids


class Solver(object):
    def __init__(self, pool, remote_repositories, installed_repository):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories

    def solve(self, request):
        return self._run_sat(request)

    def _run_sat(self, request):
        return resolve_request(self._pool, request, self._installed_repository)
