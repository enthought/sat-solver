from unittest import TestCase

from simplesat.pysolver import optimize
from .test_tools import ScenarioMixin


class TestSolverSimple(TestCase, ScenarioMixin):

    def test_simple_numpy(self):
        # Given
        scenario = 'simple_numpy.yaml'
        pool, requirement = self.parse_scenario_file(scenario)
        rules = self.generate_rules_for_requirement(pool, requirement)

        # When
        solution = optimize(pool, requirement, rules)

        # Then
        names_and_versions = [(pkg.name, str(pkg.version)) for pkg in solution]
        self.assertItemsEqual(
            names_and_versions, [('mkl', '10.3-1'), ('numpy', '1.8.1-1')])
