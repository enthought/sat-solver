from unittest import TestCase

from enstaller.solver import Request

from simplesat.pysolver_with_policy import resolve_request
from .common import parse_scenario_file


class ScenarioTestAssistant(object):

    def _check_solution(self, filename):
        # Test that the solution described in the scenario file matches with
        # what the SAT solver computes.

        # Given
        pool, requirement, expected = parse_scenario_file(filename)
        request = Request()
        request.install(requirement)

        # When
        solution = resolve_request(pool, request)

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

    SCENARIO = 'iris_php.yaml'

    def test_solution(self):
        self._check_solution(self.SCENARIO)
