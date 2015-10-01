"""
Simple algorithme based on 0installer algorithm, as described in
http://0install.net/solver.html
"""
import operator

from simplesat.pysolver_helpers import is_satisfiable
from simplesat.rules_generator import PackageRule, RulesGenerator, RuleType

from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement
from enstaller.new_solver.tests.common import repository_from_index
from enstaller.solver import Request


def sorted_candidates(pool, requirement):
    """
    Returns the sorted package metadata (highest version first), within
    the constraints defined in the given requiremet.
    """
    return sorted(pool.what_provides(requirement),
                  key=operator.attrgetter("version"), reverse=True)


def find_best_candidate(pool, requirement, rules):
    candidates = sorted_candidates(pool, requirement)

    for candidate in candidates:
        id = pool.package_id(candidate)
        new_rules = rules[:] + [PackageRule((id, ), RuleType.internal)]
        if is_satisfiable(new_rules):
            break
    else:
        raise ValueError("BOU !!!!")

    return candidate


def optimize_at_level(pool, parent_package, rules, solution):
    new_rules = rules[:]

    # Step 1: optimize each dependency independently
    best_dependencies = []

    for dependency in parent_package.dependencies:
        requirement = Requirement.from_legacy_requirement_string(dependency)
        best_candidate = find_best_candidate(pool, requirement, new_rules)

        id = pool.package_id(best_candidate)
        new_rules.append(PackageRule((id,), RuleType.internal))
        best_dependencies.append(best_candidate)

    solution.extend(best_dependencies)

    # Step 2: recurse
    for dependency in best_dependencies:
        solution = optimize_at_level(pool, dependency, new_rules, solution)

    return solution


def optimize(pool, requirement, rules):
    best_package = find_best_candidate(pool, requirement, rules)
    solution = [best_package]
    return optimize_at_level(pool, best_package, rules, solution)


if __name__ == '__main__':
    repository = repository_from_index("full_index.json")
    pool = Pool([repository])

    requirement_str = "scikit_learn < 0.14"
    requirement = Requirement._from_string(requirement_str)

    request = Request()
    request.install(requirement)

    rules_generator = RulesGenerator(pool, request)
    rules = list(rules_generator.iter_rules())

    solution = optimize(pool, requirement, rules)
    for decision in solution:
        print(decision.name, str(decision.version))
