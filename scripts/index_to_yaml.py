import argparse
import collections
import json
import operator
import sys

import six
import yaml

from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import InstallRequirement
from simplesat.constraints.package_parser import constraints_to_pretty_strings
from simplesat.constraints.kinds import (
    Any, EnpkgUpstreamMatch, Equal
)
from simplesat.package import (
    PackageMetadata, RepositoryInfo, RepositoryPackageMetadata
)
from simplesat.repository import Repository


def parse_index_packages_to_install_requires(packages):
    name_to_install_requires = {}

    for dependency in packages:
        parts = dependency.split(None, 1)
        name = parts[0]
        name_to_install_requires.setdefault(name, [])

        if len(parts) == 1:
            constraint = "*"
        else:
            version_part = parts[1]
            package_version = EnpkgVersion.from_string(version_part)
            if package_version.build == 0:
                constraint = "^= {0}".format(version_part)
            else:
                constraint = "== {0}".format(version_part)

        name_to_install_requires[name].append(constraint)

    return dict(
        (name, tuple(value))
        for name, value in six.iteritems(name_to_install_requires)
    )


def repository_from_index(index_path):
    with open(index_path, "rt") as fp:
        json_dict = json.load(fp)

    repository = Repository()
    repository_info = RepositoryInfo("remote")

    for key, entry in six.iteritems(json_dict):
        raw_name = key.split("-")[0]
        version_string = "{0}-{1}".format(entry["version"], entry["build"])
        version = EnpkgVersion.from_string(version_string)
        name_to_install_requires =  parse_index_packages_to_install_requires(
            entry.get("packages", [])
        )
        install_requires = tuple(
            (name, (constraints,))
            for name, constraints in six.iteritems(name_to_install_requires)
        )
        package = RepositoryPackageMetadata(
            PackageMetadata(raw_name, version, install_requires), repository_info
        )
        repository.add_package(package)

    return repository


def dependency_to_string(dependency):
    req = InstallRequirement._from_string(dependency)
    constraints = list(req._constraints._constraints)
    assert len(constraints) == 1
    assert isinstance(constraints[0],
                      (EnpkgUpstreamMatch, Any, Equal))
    constraint = constraints[0]
    if isinstance(constraint, Any):
        return req.name
    elif isinstance(constraint, Equal):
        return "{0} == {1}".format(req.name, str(constraint.version))
    else:  # EnpkgUpstreamMatch
        assert isinstance(constraint.version, EnpkgVersion)
        return "{0} ^= {1}".format(req.name, str(constraint.version.upstream))


def requirements_string(package):
    name = package.name
    template = "{name} {version}"
    if len(package.install_requires) > 0:
        template += "; depends ({install_requires})"
    install_requires = ', '.join(
        dependency_to_string(dep)
        for dep in constraints_to_pretty_strings(package.install_requires))
    return template.format(
        name=name, version=package.version, install_requires=install_requires)


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("index")

    ns = p.parse_args(argv)

    repository = repository_from_index(ns.index)

    data = collections.defaultdict(list)

    for package in repository:
        data["packages"].append(requirements_string(package))

    data = dict(data)
    yaml.safe_dump(data, sys.stdout, allow_unicode=True,
                   width=100000, default_flow_style=False)


if __name__ == "__main__":
    main()
