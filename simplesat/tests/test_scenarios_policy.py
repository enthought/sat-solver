import os.path

from unittest import TestCase, expectedFailure

from egginst.errors import NoPackageFound
from enstaller.new_solver import Pool

from simplesat.dependency_solver import DependencySolver
from .common import Scenario
from simplesat.transaction import FailureOperation


class ScenarioTestAssistant(object):

    def _check_solution(self, filename):
        # Test that the solution described in the scenario file matches with
        # what the SAT solver computes.

        # Given
        scenario = Scenario.from_yaml(
            os.path.join(os.path.dirname(__file__), filename)
        )
        request = scenario.request

        # When
        pool = Pool(scenario.remote_repositories)
        pool.add_repository(scenario.installed_repository)
        solver = DependencySolver(
            pool, scenario.remote_repositories, scenario.installed_repository
        )
        transaction = solver.solve(request)

        # Then
        self.assertEqualFailures(transaction.operations, scenario.operations)
        self.assertEqualOperations(transaction.operations, scenario.operations)

    def assertEqualFailures(self, operations, scenario_operations):
        solver_fail = (
            len(operations) > 0 and
            issubclass(type(operations[0]), FailureOperation)
        )
        scenario_fail = (
            len(scenario_operations) > 0 and
            issubclass(type(scenario_operations[0]), FailureOperation)
        )

        if solver_fail and scenario_fail:
            # Expected failures are OK, we're done!
            operations.pop(0)
            scenario_operations.pop(0)
            return
        elif solver_fail and not scenario_fail:
            msg = "Solver unexpectedly failed"
            failed_op = operations[0]
            if failed_op.reason:
                msg += " because {}".format(failed_op.reason)
            self.fail(msg)
        elif scenario_fail and not solver_fail:
            failed_op = scenario_operations[0]
            msg = "Solver unexpectedly succeeded, but {}."
            self.fail(msg.format(failed_op.reason))

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
    @expectedFailure
    def test_crash(self):
        self._check_solution("crash.yaml")

    def test_simple_numpy(self):
        self._check_solution("simple_numpy.yaml")

    def test_ipython(self):
        self._check_solution("ipython.yaml")

    def test_iris(self):
        self._check_solution("iris.yaml")

    def test_no_candidate(self):
        with self.assertRaises(NoPackageFound):
            self._check_solution("no_candidate.yaml")


class TestInstallSet(TestCase, ScenarioTestAssistant):

    def test_simple_numpy(self):
        self._check_solution("simple_numpy_installed.yaml")

    def test_ipython(self):
        self._check_solution("ipython_with_installed.yaml")
