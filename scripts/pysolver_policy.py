import argparse

from enstaller.new_solver.yaml_utils import Scenario
from enstaller.new_solver import Pool

from simplesat.pysolver_with_policy import resolve_request


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    ns = p.parse_args()

    scenario = Scenario.from_yaml(ns.scenario)
    pool = Pool(scenario.remote_repositories)
    request = scenario.request

    packages = resolve_request(pool, request)

    for package in packages:
        package_id = pool.package_id(package)
        print pool.id_to_string(package_id)
