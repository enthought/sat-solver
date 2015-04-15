import os.path

from unittest import TestCase, expectedFailure

from enstaller.new_solver import Pool

from simplesat.pysolver_with_policy import Solver
from .common import Scenario


class ScenarioTestAssistant(object):

    def _check_solution(self, filename):
        # Test that the solution described in the scenario file matches with
        # what the SAT solver computes.

        # Given
        scenario = Scenario.from_yaml(os.path.join(os.path.dirname(__file__), 
                                      filename))
        request = scenario.request

        # When
        pool = Pool(scenario.remote_repositories)
        pool.add_repository(scenario.installed_repository)
        solver = Solver(pool, scenario.remote_repositories,
                        scenario.installed_repository)
        decisions_set = solver.solve(request)

        # Then
        positive_decisions = set(decision for decision in decisions_set
                                 if decision > 0)
        self.assertItemsEqual(positive_decisions,
                              scenario.decisions.keys())


class TestNoInstallSet(TestCase, ScenarioTestAssistant):

    def test_simple_numpy(self):
        self._check_solution("simple_numpy.yaml")

    def test_ipython(self):
        self._check_solution("ipython.yaml")

    # This one is known to fail because the InstalledPolicy currently
    # causes spurious dependencies to be pulled in.
    @expectedFailure
    def test_iris(self):
        self._check_solution("iris.yaml")


class TestInstallSet(TestCase, ScenarioTestAssistant):

    def test_simple_numpy(self):
        self._check_solution("simple_numpy_installed.yaml")

    def test_ipython(self):
        self._check_solution("ipython_with_installed.yaml")
