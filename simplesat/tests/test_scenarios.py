import os
import re
from unittest import TestCase

import yaml

from enstaller.repository import PackageMetadata
from enstaller import Repository
from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement
from enstaller.new_solver.constraints_parser import (
    _RawRequirementParser
)
from enstaller.new_solver.constraint_types import (
    Any, EnpkgUpstreamMatch, Equal
)
from enstaller.solver import Request
from enstaller.versions.enpkg import EnpkgVersion

from simplesat.pysolver import optimize
from simplesat.rules_generator import RulesGenerator

HERE = os.path.dirname(__file__)

PACKAGE_RE = re.compile("""
    (?P<name>\w+)
    -
    (?P<version>[^;\s]+)  # Anything but whitespace and semi-colon.
    \s*
    (
        ;\s*
        depends
        \s*
        \(
        (?P<dependencies>.*)
        \)
    )?
""", flags=re.VERBOSE)


def scenario_factory(filename):
    with open(filename) as fp:
        data = yaml.load(fp)
    packages = data.get('packages', [])
    request = data['request']
    assert len(request) == 1
    step = request[0]
    assert step['operation'] == 'install'
    requirement_str = step['requirement']
    requirement = Requirement._from_string(requirement_str)

    repository = Repository()

    parser = _RawRequirementParser()
    for package_str in packages:
        m = PACKAGE_RE.match(package_str)
        assert m is not None
        results = m.groupdict()

        name = results['name']
        version = EnpkgVersion.from_string(results['version'])
        dependencies_str = results['dependencies']
        if dependencies_str is not None:
            constraints = parser.parse(dependencies_str, EnpkgVersion.from_string)

            legacy_constraints = []
            for constraint_name, constraint_set in constraints.items():
                assert len(constraint_set) == 1
                constraint = constraint_set.pop()
                assert isinstance(constraint,
                                  (EnpkgUpstreamMatch, Any, Equal))
                if isinstance(constraint, Any):
                    legacy_constraint = constraint_name
                elif isinstance(constraint, Equal):
                    legacy_constraint = (
                        constraint_name + ' ' + str(constraint.version))
                else:  # EnpkgUpstreamMatch
                    assert isinstance(constraint.version, EnpkgVersion)
                    legacy_constraint = (
                        constraint_name + ' ' + str(constraint.version.upstream))
                legacy_constraints.append(legacy_constraint)
        else:
            legacy_constraints = []
        package = PackageMetadata(name + '-' + str(version),
                                  name,
                                  version,
                                  legacy_constraints,
                                  '2.7')

        repository.add_package(package)

    return Pool([repository]), requirement


class TestSolverSimple(TestCase):

    def test_simple_numpy(self):

        pool, requirement = scenario_factory(os.path.join(HERE, 'simple_numpy.yaml'))

        request = Request()
        request.install(requirement)

        rules_generator = RulesGenerator(pool, request)
        rules = list(rules_generator.iter_rules())

        solution = optimize(pool, requirement, rules)

        names_and_versions = [
            (pkg.name, str(pkg.version)) for pkg in solution
        ]
        self.assertItemsEqual(names_and_versions,
                              [('mkl', '10.3-1'), ('numpy', '1.8.1-1')])
