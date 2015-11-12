from __future__ import print_function

import argparse
import sys

from enstaller.new_solver import Pool
from enstaller.new_solver.yaml_utils import Scenario

from simplesat.dependency_solver import DependencySolver


def solve_and_print(request, remote_repositories, installed_repository,
                    print_ids, prune=True):
    pool = Pool(remote_repositories)
    pool.add_repository(installed_repository)

    solver = DependencySolver(
        pool, remote_repositories, installed_repository, use_pruning=prune)
    transaction = solver.solve(request)
    print(transaction)
    print("Solve time:", solver._last_solve_time, file=sys.stderr)


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    p.add_argument("--print-ids", action="store_true")
    p.add_argument("--no-prune", action="store_false")

    ns = p.parse_args(argv)

    scenario = Scenario.from_yaml(ns.scenario)
    solve_and_print(scenario.request, scenario.remote_repositories,
                    scenario.installed_repository, ns.print_ids, ns.no_prune)


if __name__ == '__main__':
    main()
