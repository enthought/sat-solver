import os.path

from unittest import TestCase, expectedFailure

from enstaller.new_solver import Pool

from simplesat.pysolver_with_policy import Solver, resolve_request
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
        transaction = solver.solve(request)

        # Then
        self.assertEqualOperations(transaction.operations,
                                   scenario.operations)

    def assertEqualOperations(self, operations, scenario_operations):
        for i, (left, right) in enumerate(zip(operations, scenario_operations)):
            if not type(left) == type(right):
                msg = "Item {0!r} differ in kinds: {1!r} vs {2!r}"
                self.fail(msg.format(i, type(left), type(right)))
            left_s = "{0} {1}".format(left.package.name,
                                      left.package.version)
            right_s = right.package
            if left_s != right_s:
                msg = "Item {0!r}: {1!r} vs {2!r}".format(i, left_s, right_s)
                self.fail(msg)

        if len(operations) != len(scenario_operations):
            self.fail("Length of operations differ")


class TestNoInstallSet(TestCase, ScenarioTestAssistant):

    def test_simple_numpy(self):
        self._check_solution("simple_numpy.yaml")

    def test_ipython(self):
        self._check_solution("ipython.yaml")

    def test_iris(self):
        self._check_solution("iris.yaml")


class TestInstallSet(TestCase, ScenarioTestAssistant):

    def test_simple_numpy(self):
        self._check_solution("simple_numpy_installed.yaml")

    def test_ipython(self):
        self._check_solution("ipython_with_installed.yaml")
