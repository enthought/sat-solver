import argparse
import sys

from enstaller.new_solver import Pool
from enstaller.new_solver.yaml_utils import Scenario

from simplesat.pysolver_with_policy import Solver
from simplesat.rules_generator import PackageRule


def print_rules(request, remote_repositories, installed_repository,
                    print_ids):
    pool = Pool(remote_repositories)
    pool.add_repository(installed_repository)

    solver = Solver(pool, remote_repositories, installed_repository)
    rules, _ = solver._create_rules_and_policy(request)
    for rule in rules:
        print(rule.to_string(pool))


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")

    ns = p.parse_args(argv)

    scenario = Scenario.from_yaml(ns.scenario)
    solve_and_print(scenario.request, scenario.remote_repositories,
                    scenario.installed_repository, ns.print_ids)


if __name__ == '__main__':
    main()
