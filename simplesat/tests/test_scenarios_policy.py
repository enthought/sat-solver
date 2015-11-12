import os.path

from unittest import TestCase

from egginst.errors import NoPackageFound
from enstaller.new_solver import Pool

from simplesat.errors import SatisfiabilityError
from simplesat.dependency_solver import DependencySolver
from .common import Scenario


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

        # Then
        try:
            transaction = solver.solve(request)
        except SatisfiabilityError as failure:
            if not scenario.failed:
                msg = "Solver unexpectedly failed"
                if failure.reason:
                    msg += " because {}".format(failure.reason)
                self.fail(msg)
        else:
            if scenario.failed:
                msg = "Solver unexpectedly succeeded, but {}."
                self.fail(msg.format(scenario.failure))
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


class TestNoInstallSet(ScenarioTestAssistant, TestCase):

    def test_directly_implied_solution(self):
        self._check_solution("directly_implied_solution.yaml")

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

    def test_blocked_upgrade(self):
        self._check_solution("simple_numpy_installed_blocking.yaml")

    def test_blocked_downgrade(self):
        self._check_solution("simple_numpy_installed_blocking_downgrade.yaml")
