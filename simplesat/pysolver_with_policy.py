from simplesat.policy import InstalledFirstPolicy
from simplesat.pysolver_helpers import solver_from_rules_set, solve_sat
from simplesat.rules_generator import RulesGenerator


def resolve_request(pool, request):
    """Given an install request, provide a list of packages
    to be installed to resolve this request, or None if no
    resolution could be found.

    """
    policy = InstalledFirstPolicy(pool)

    assert len(request.jobs) == 1
    job = request.jobs[0]
    assert job.kind == 'install'
    requirement = job.requirement

    requirement_ids = [
        pool.package_id(package) for package in pool.what_provides(requirement)
    ]
    policy.add_packages_by_id(requirement_ids)

    rules_generator = RulesGenerator(pool, request)
    rules = list(rules_generator.iter_rules())

    s = solver_from_rules_set(rules, policy)
    solution_ids = solve_sat(s)

    return [pool._id_to_package[id] for id in solution_ids if id > 0]
