import os.path

from unittest import TestCase

from enstaller.new_solver import Pool
from enstaller.solver import JobType

from simplesat.pysolver import optimize
from .common import Scenario, generate_rules_for_requirement


def _get_requirement_from_request_block(request):
    assert len(request.jobs) == 1
    job = request.jobs[0]
    assert job.kind == JobType.install
    return job.requirement
    #return Requirement._from_string(requirement_str)


class ScenarioTestAssistant(object):

    def _check_solution(self, filename):
        # Test that the solution described in the scenario file matches with
        # what the SAT solver computes.

        # Given
        scenario = Scenario.from_yaml(os.path.join(os.path.dirname(__file__), 
                                      filename))
        pool = Pool(scenario.remote_repositories)
        requirement = _get_requirement_from_request_block(scenario.request)
        rules = generate_rules_for_requirement(pool, requirement)

        # When
        solution = optimize(pool, requirement, rules)

        # Then
        decisions = set(pool.package_id(p) for p in solution)
        self.assertItemsEqual(decisions, scenario.decisions.keys())


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
