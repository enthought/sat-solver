import argparse
import sys


from simplesat.dependency_solver import DependencySolver
from simplesat.pool import Pool
from simplesat.test_utils import Scenario


def print_rules(request, remote_repositories, installed_repository):
    pool = Pool(remote_repositories)
    pool.add_repository(installed_repository)

    solver = DependencySolver(pool, remote_repositories, installed_repository)
    _, rules = solver._create_rules_and_initialize_policy(request)
    for rule in rules:
        print(rule.to_string(pool))


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")

    ns = p.parse_args(argv)

    scenario = Scenario.from_yaml(ns.scenario)
    print_rules(scenario.request, scenario.remote_repositories,
                scenario.installed_repository)


if __name__ == '__main__':
    main()
