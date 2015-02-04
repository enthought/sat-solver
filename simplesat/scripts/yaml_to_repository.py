"""Convert YAML scenario file to PHP composer-compatible format.
"""

import argparse
import sys

import yaml

from enstaller import Repository
from enstaller.new_solver._composer_utils import repository_to_composer_json
from enstaller.new_solver.package_parser import PrettyPackageStringParser
from enstaller.versions.enpkg import EnpkgVersion


def yaml_to_repository(path):
    with open(path) as fp:
        data = yaml.load(fp)

    packages = data.get('packages', [])
    repository = Repository()

    parser = PrettyPackageStringParser(EnpkgVersion.from_string)
    for package_str in packages:
        package = parser.parse_to_package(package_str, "2.7")
        repository.add_package(package)

    return repository


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Yaml scenario file")
    ns = p.parse_args(sys.argv[1:])

    path = ns.scenario
    repository = yaml_to_repository(path)

    composer_json = repository_to_composer_json(repository)
    print(composer_json)


if __name__ == '__main__':
    main()
