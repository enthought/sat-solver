import argparse
import sys

from enstaller.new_solver import Pool
from enstaller.new_solver.yaml_utils import Scenario

from simplesat.pysolver_with_policy import Solver


def solve_and_print(request, remote_repositories, installed_repository,
                    print_ids):
    pool = Pool(remote_repositories)
    pool.add_repository(installed_repository)

    solver = Solver(pool, remote_repositories, installed_repository)
    transaction = solver.solve(request)
    print(transaction)


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    p.add_argument("--print-ids", action="store_true")

    ns = p.parse_args(argv)

    scenario = Scenario.from_yaml(ns.scenario)
    solve_and_print(scenario.request, scenario.remote_repositories,
                    scenario.installed_repository, ns.print_ids)


if __name__ == '__main__':
    main()
