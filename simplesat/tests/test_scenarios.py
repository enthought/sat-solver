from unittest import TestCase

from simplesat.pysolver import optimize
from .test_tools import ScenarioMixin


class TestSolverSimple(TestCase, ScenarioMixin):

    def test_simple_numpy(self):
        # Given
        scenario = 'simple_numpy.yaml'

        pool, requirement, expected = self.parse_scenario_file(scenario)
        rules = self.generate_rules_for_requirement(pool, requirement)

        # When
        solution = optimize(pool, requirement, rules)

        # Then
        self.assertItemsEqual(solution, expected)

    def test_ipython(self):
        # Given
        scenario = 'ipython.yaml'

        # When
        pool, requirement, expected = self.parse_scenario_file(scenario)
        rules = self.generate_rules_for_requirement(pool, requirement)

        # When
        solution = optimize(pool, requirement, rules)

        # Then
        self.assertItemsEqual(solution, expected)
