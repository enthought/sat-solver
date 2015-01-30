import sys

import yaml

from simplesat.policy import InstalledFirstPolicy
from simplesat.pysolver_helpers import solver_from_rules_set, solve_sat
from simplesat.rules_generator import RulesGenerator
from simplesat.tests.common import (
    _construct_pool, _get_requirement_from_request_block)

from enstaller.new_solver.package_parser import PrettyPackageStringParser
from enstaller.solver import Request
from enstaller.versions.enpkg import EnpkgVersion


def _construct_package_list(pool, installed_data):
    # This is completely horrible...

    package_ids = []
    parser = PrettyPackageStringParser(EnpkgVersion.from_string)
    for package_str in packages_data:
        package = parser.parse_to_package(package_str, "2.7")
        for candidate in pool._packages_by_name.get(package.name, []):
            if candidate.version == package.version:
                package_ids.append(candidate.id)
                break
        else:
            raise ValueError("No match found for {}".format(package))

    return package_ids


def check_solution(rules, solution):
    for rule in rules:
        if not set(rule.literals) & set(solution):
            return False
    return True


if __name__ == '__main__':
    scenario_path = sys.argv[1]

    with open(scenario_path) as fp:
        data = yaml.load(fp)

    packages_data = data.get('packages', [])
    pool = _construct_pool(packages_data)

    request_data = data['request']
    requirement = _get_requirement_from_request_block(request_data)
    request = Request()
    request.install(requirement)

    installed_data = data.get('installed', [])
    installed_ids = _construct_package_list(pool, installed_data)

    policy = InstalledFirstPolicy(pool, installed_ids)

    rules_generator = RulesGenerator(pool, request)
    rules = list(rules_generator.iter_rules())

    s = solver_from_rules_set(rules)
    solution_ids = solve_sat(s)
    for package_id in solution_ids:
        if package_id > 0:
            print pool.id_to_string(package_id)

    # Check the solution, just to make sure.
    print check_solution(rules, solution_ids)
