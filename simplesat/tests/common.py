import collections
import os

import yaml

from enstaller import Repository
from enstaller.new_solver.package_parser import PrettyPackageStringParser
from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement
from enstaller.package import RepositoryPackageMetadata
from enstaller.repository_info import BroodRepositoryInfo
from enstaller.solver import Request
from enstaller.utils import PY_VER
from enstaller.versions.enpkg import EnpkgVersion

from simplesat.rules_generator import RulesGenerator
from simplesat.transaction import (
    FailureOperation, InstallOperation, RemoveOperation, UpdateOperation
)


HERE = os.path.dirname(__file__)


def generate_rules_for_requirement(pool, requirement, installed_map=None):
    """Generate CNF rules for a requirement.

    Parameters
    ----------
    pool: Pool
        Package constraints.
    requirement: Requirement
        Package to be installed.

    Returns
    -------
    rules: list
        Package rules describing the given scenario.
    """
    request = Request()
    request.install(requirement)

    rules_generator = RulesGenerator(pool, request, installed_map)
    rules = list(rules_generator.iter_rules())
    return rules


def parse_package_list(packages):
    """ Yield PackageMetadata instances given an sequence  of pretty package
    strings.

    Parameters
    ----------
    packages : iterator
        An iterator of package strings (e.g.
        'numpy 1.8.1-1; depends (MKL ~= 10.3)').
    """
    parser = PrettyPackageStringParser(EnpkgVersion.from_string)

    for package_str in packages:
        package = parser.parse_to_package(package_str, PY_VER)
        full_name = "{0} {1}".format(package.name, package.full_version)
        yield full_name, package


def repository_factory(package_names, repository_info, reference_packages):
    repository = Repository()
    for package_name in package_names:
        package = reference_packages[package_name]
        package = RepositoryPackageMetadata.from_package(package, repository_info)
        repository.add_package(package)
    return repository


def remote_repository(yaml_data, packages):
    repository_info = BroodRepositoryInfo("http://acme.come", "remote")
    package_names = yaml_data.get("remote", packages.keys())
    return repository_factory(package_names, repository_info, packages)


def installed_repository(yaml_data, packages):
    repository_info = BroodRepositoryInfo("http://acme.come", "installed")
    package_names = yaml_data.get("installed", [])
    return repository_factory(package_names, repository_info, packages)


class Scenario(object):
    @classmethod
    def from_yaml(cls, filename):
        with open(filename) as fp:
            data = yaml.load(fp)

        packages = collections.OrderedDict(
            parse_package_list(data.get("packages", []))
        )
        operations = data.get("request", [])

        request = Request()

        for operation in operations:
            kind = operation["operation"]
            requirement = Requirement._from_string(operation["requirement"])
            getattr(request, kind)(requirement)

        decisions = data.get("decisions", {})

        operations = []
        for operation in data.get("transaction", []):
            if operation["kind"] == "install":
                operations.append(InstallOperation(operation["package"]))
            elif operation["kind"] == "update":
                operations.append(UpdateOperation(operation["from"],
                                                  operation["to"]))
            elif operation["kind"] == "remove":
                operations.append(RemoveOperation(operation["package"]))
            elif operation["kind"] == "fail":
                operations.append(FailureOperation(operation['reason']))
            else:
                msg = "invalid operation kind {!r}".format(operation["kind"])
                raise ValueError(msg)

        return cls(packages, [remote_repository(data, packages)],
                   installed_repository(data, packages), request,
                   decisions, operations)

    def __init__(self, packages, remote_repositories, installed_repository,
                 request, decisions, operations):
        self.packages = packages
        self.remote_repositories = remote_repositories
        self.installed_repository = installed_repository
        self.request = request
        self.decisions = decisions
        self.operations = operations

    def print_solution(self, pool, positive_decisions):
        for package_id in sorted(positive_decisions):
            package = pool._id_to_package[package_id]
            print("{}: {} {}".format(package_id, package.name,
                                     package.full_version))
