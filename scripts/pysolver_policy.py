import argparse

from enstaller.new_solver import Pool
from enstaller.new_solver.yaml_utils import Scenario

from simplesat.pysolver_with_policy import resolve_request


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    ns = p.parse_args()

    scenario = Scenario.from_yaml(ns.scenario)
    pool = Pool(scenario.remote_repositories)
    request = scenario.request

    # This is very hacky...
    installed = []
    remote = scenario.remote_repositories[0]
    for pkg_list in scenario.installed_repository._name_to_packages.values():
        for package in pkg_list:
            installed.append(
                remote.find_package(package.name, str(package.version))
            )

    signed_package_ids = resolve_request(pool, request, installed)
    for signed_id in signed_package_ids:
        print pool.id_to_string(signed_id)
