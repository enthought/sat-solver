import argparse
import sys

from enstaller.new_solver import Pool
from enstaller.new_solver.yaml_utils import Scenario

from simplesat.pysolver_with_policy import resolve_request


def solve(request, remote_repositories, installed_repository):
    pool = Pool(remote_repositories)

    # This is very hacky...
    installed = []
    remote = remote_repositories[0]
    for pkg_list in installed_repository._name_to_packages.values():
        for package in pkg_list:
            installed.append(
                remote.find_package(package.name, str(package.version))
            )

    signed_ids = resolve_request(pool, request, installed)
    for signed_id in signed_ids:
        print(pool.id_to_string(signed_id))


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    ns = p.parse_args(argv)

    scenario = Scenario.from_yaml(ns.scenario)
    solve(scenario.request, scenario.remote_repositories,
          scenario.installed_repository)


if __name__ == '__main__':
    main()
