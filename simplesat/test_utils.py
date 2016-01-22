import collections
import os

import six
import yaml

from okonomiyaki.platforms import PythonImplementation
from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import PrettyPackageStringParser, Requirement
from simplesat.package import RepositoryInfo, RepositoryPackageMetadata
from simplesat.repository import Repository
from simplesat.request import Request
from simplesat.rules_generator import RulesGenerator
from simplesat.transaction import (
    InstallOperation, RemoveOperation, UpdateOperation
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
        'numpy 1.8.1-1; depends (MKL ^= 10.3)').
    """
    parser = PrettyPackageStringParser(EnpkgVersion.from_string)

    for package_str in packages:
        package = parser.parse_to_package(package_str)
        full_name = "{0} {1}".format(package.name, str(package.version))
        yield full_name, package


def repository_factory(package_names, repository_info, reference_packages):
    repository = Repository()
    for package_name in package_names:
        package = reference_packages[package_name]
        package = RepositoryPackageMetadata(package, repository_info)
        repository.add_package(package)
    return repository


def remote_repository(yaml_data, packages):
    repository_info = RepositoryInfo(u"remote")
    package_names = yaml_data.get("remote", packages.keys())
    return repository_factory(package_names, repository_info, packages)


def installed_repository(yaml_data, packages):
    repository_info = RepositoryInfo(u"installed")
    package_names = yaml_data.get("installed", [])
    return repository_factory(package_names, repository_info, packages)


class Scenario(object):

    @classmethod
    def from_yaml(cls, file_or_filename):
        if isinstance(file_or_filename, six.string_types):
            with open(file_or_filename) as fp:
                data = yaml.load(fp, Loader=_UnicodeLoader)
        else:
            data = yaml.load(file_or_filename, Loader=_UnicodeLoader)

        packages = collections.OrderedDict(
            parse_package_list(data.get("packages", []))
        )
        scenario_requests = data.get("request", [])

        marked = list(data.get("marked", []))

        request = Request()

        update_all = False

        for s_request in scenario_requests:
            kind = s_request["operation"]
            if kind == 'update_all':
                update_all = True
                continue
            requirement = Requirement._from_string(s_request["requirement"])
            try:
                marked.remove(requirement.name)
            except ValueError:
                pass
            getattr(request, kind)(requirement)

        if update_all:
            request_job = request.update
        else:
            request_job = request.install

        for package_str in marked:
            request_job(Requirement._from_string(package_str))

        decisions = data.get("decisions", {})

        def P(p):
            return next(parse_package_list([p]))[1]

        operations = []
        for operation in data.get("transaction", []):
            if operation["kind"] == "install":
                operations.append(InstallOperation(P(operation["package"])))
            elif operation["kind"] == "update":
                operations.append(UpdateOperation(P(operation["to"]),
                                                  P(operation["from"])))
            elif operation["kind"] == "remove":
                operations.append(RemoveOperation(P(operation["package"])))
            else:
                msg = "invalid operation kind {!r}".format(operation["kind"])
                raise ValueError(msg)

        failure = data.get('failure')

        return cls(packages, [remote_repository(data, packages)],
                   installed_repository(data, packages), request,
                   decisions, operations, failure)

    def __init__(self, packages, remote_repositories, installed_repository,
                 request, decisions, operations, failure=None):
        self.packages = packages
        self.remote_repositories = remote_repositories
        self.installed_repository = installed_repository
        self.request = request
        self.decisions = decisions
        self.operations = operations
        self.failure = failure

    @property
    def failed(self):
        return self.failure is not None

    def print_solution(self, pool, positive_decisions):
        for package_id in sorted(positive_decisions):
            package = pool._id_to_package[package_id]
            print("{}: {} {}".format(package_id, package.name,
                                     package.full_version))


def construct_yaml_str(self, node):
    # Override the default string handling function to always
    # return unicode objects
    return self.construct_scalar(node)


class _UnicodeLoader(yaml.Loader):
    pass


_UnicodeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
