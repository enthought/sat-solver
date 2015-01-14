import operator
import sys

from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement
from enstaller.new_solver.tests.common import repository_from_index
from enstaller.solver import Request
from enstaller.versions.enpkg import EnpkgVersion

from simplesat.minisat_helpers import (is_satisfable, rules_set_to_dimacs,
                                       solution_to_package_strings, solve_sat)
from simplesat.rules_generator import PackageRule, RulesGenerator

V = EnpkgVersion.from_string


def sorted_candidates(pool, requirement):
    """
    Returns the sorted package metadata (highest version first), within
    the constraints defined in the given requiremet.
    """
    return sorted(pool.what_provides(requirement),
                  key=operator.attrgetter("version"), reverse=True)


def compute_sat(pool, rules):
    decisions = solve_sat(pool, rules)

    for decision in decisions:
        if decision > 0:
            print(pool.id_to_string(decision))


repository = repository_from_index("full_index.json")
pool = Pool([repository])

requirement_str = "scikit_learn < 0.14"
requirement = Requirement._from_string(requirement_str)

# if False:
#     candidates = pool.what_provides(requirement)
#     for candidate in sorted(candidates,
#                             key=operator.attrgetter("version")):
#         print(pool.id_to_string(candidate.id))

request = Request()
request.install(requirement)

rules_generator = RulesGenerator(pool, request)
rules = list(rules_generator.iter_rules())

#for rule in rules:
#    print rule.to_string(pool)
#sys.exit(0)

## Naive, pure SAT
#compute_sat(pool, rules)


def find_best_candidate(pool, requirement, rules):
    candidates = sorted_candidates(pool, requirement)

    for candidate in candidates:
        new_rules = rules[:] + [PackageRule((candidate.id,)),]
        if is_satisfable(pool, new_rules):
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

        new_rules.append(PackageRule((best_candidate.id,)))
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


solution = optimize(pool, requirement, rules)
for decision in solution:
    print(decision.name, str(decision.version))
