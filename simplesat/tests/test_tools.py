import os

import yaml

from enstaller import Repository
from enstaller.new_solver.package_parser import PrettyPackageStringParser
from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement
from enstaller.solver import Request
from enstaller.versions.enpkg import EnpkgVersion

from simplesat.rules_generator import RulesGenerator


class ScenarioMixin(object):

    HERE = os.path.dirname(__file__)

    def parse_scenario_file(self, filename):
        """Parses a YAML scenario file.

        Parameters
        ----------
        filename: str
            Path of a scenario file, relative to the directory of this file.

        Returns
        -------
        pool: Pool instance
            Pool containing the packages contained in the scenario file.
        requirement: Requirement instance
            Requirement describing the package to be installed.

        """
        path = os.path.join(self.HERE, filename)
        with open(path) as fp:
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

        pool = Pool([repository])

        solution = []
        solution_strings = data['solution']
        for solution_str in solution_strings:
            package_str = '-'.join(solution_str.split())
            r = Requirement.from_package_string(package_str)
            solution.extend(pool.what_provides(r))

        return pool, requirement, solution

    def generate_rules_for_requirement(self, pool, requirement):
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

        rules_generator = RulesGenerator(pool, request)
        rules = list(rules_generator.iter_rules())
        return rules
