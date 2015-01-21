import os
from unittest import TestCase

import yaml


from enstaller import Repository
from enstaller.new_solver.package_parser import PrettyPackageStringParser
from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement

from enstaller.solver import Request
from enstaller.versions.enpkg import EnpkgVersion

from simplesat.pysolver import optimize
from simplesat.rules_generator import RulesGenerator

HERE = os.path.dirname(__file__)


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

    parser = PrettyPackageStringParser(EnpkgVersion.from_string)
    for package_str in packages:
        package = parser.parse_to_package(package_str, "2.7")
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
