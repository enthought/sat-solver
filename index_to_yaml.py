from enstaller.egg_meta import split_eggname
from enstaller.new_solver.tests.common import repository_from_index
from enstaller.new_solver.requirement import Requirement
from enstaller.new_solver.constraint_types import (
    Any, EnpkgUpstreamMatch, Equal
)
from enstaller.versions.enpkg import EnpkgVersion


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
    template = "{name} {version}"
    if len(package.dependencies) > 0:
        template += "; depends ({dependencies})"
    dependencies = ', '.join(
        dependency_to_string(dep) for dep in package.dependencies)
    raw_name, _, _ = split_eggname(package.key)
    return template.format(
        name=raw_name, version=package.version, dependencies=dependencies)


repository = repository_from_index('filtered_full_index.json')
for package in repository.iter_packages():
    # print package.name
    # print str(package.version)
    # print package.dependencies
    print requirements_string(package)
