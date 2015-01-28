from unittest import TestCase

from simplesat.pysolver import optimize
from .common import generate_rules_for_requirement, parse_scenario_file


class ScenarioTestAssistant(object):

    def _check_solution(self, filename):
        # Test that the solution described in the scenario file matches with
        # what the SAT solver computes.

        # Given
        pool, requirement, expected = parse_scenario_file(filename)
        rules = generate_rules_for_requirement(pool, requirement)

        # When
        solution = optimize(pool, requirement, rules)

        # Then
        self.assertItemsEqual(solution, expected)


class TestSimpleNumpy(TestCase, ScenarioTestAssistant):

    SCENARIO = 'simple_numpy.yaml'

    def test_solution(self):
        self._check_solution(self.SCENARIO)


class TestIPython(TestCase, ScenarioTestAssistant):

    SCENARIO = 'ipython.yaml'

    def test_solution(self):
        self._check_solution(self.SCENARIO)


class TestIris(TestCase, ScenarioTestAssistant):

    SCENARIO = 'iris.yaml'

    def test_solution(self):
        self._check_solution(self.SCENARIO)
