import argparse
import collections
import operator
import sys

import yaml

from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import Requirement
from simplesat.constraints.kinds import (
    Any, EnpkgUpstreamMatch, Equal
)
from simplesat.test_utils import repository_from_index



# TODO Can use new enstaller pretty printer here...

def dependency_to_string(dependency):
    req = Requirement.from_legacy_requirement_string(dependency)
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
        return "{0} ~= {1}".format(req.name, str(constraint.version.upstream))


def requirements_string(package):
    name = package.key.split("-")[0]
    template = "{name} {version}"
    if len(package.dependencies) > 0:
        template += "; depends ({dependencies})"
    dependencies = ', '.join(
        dependency_to_string(dep) for dep in package.dependencies)
    return template.format(
        name=name, version=package.version, dependencies=dependencies)


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("index")

    ns = p.parse_args(argv)

    repository = repository_from_index(ns.index)

    data = collections.defaultdict(list)

    for package in sorted(repository.iter_packages(),
                          key=operator.attrgetter("name")):
        data["packages"].append(requirements_string(package))

    data = dict(data)
    yaml.safe_dump(data, sys.stdout, allow_unicode=True,
                   width=100000, default_flow_style=False)


if __name__ == "__main__":
    main()
