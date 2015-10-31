import os.path

from unittest import TestCase

from enstaller.new_solver import Pool

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
        transaction = solver.solve(request)

        # Then
        self.assertEqualOperations(transaction.operations,
                                   scenario.operations)

    def _pkg_delta(self, operations, scenario_operations):
        pkg_delta = {}
        for p in scenario_operations:
            name, version = p.package.split()
            pkg_delta.setdefault(name, [None, None])[0] = version
        for p in operations:
            name = p.package.name
            version = str(p.package.version)
            pkg_delta.setdefault(name, [None, None])[1] = version
        for n, v in pkg_delta.items():
            if v[0] == v[1]:
                pkg_delta.pop(n)
        return pkg_delta

    def assertEqualOperations(self, operations, scenario_operations):
        pairs = zip(operations, scenario_operations)
        for i, (left, right) in enumerate(pairs):
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

    def test_crash(self):
        self._check_solution("crash.yaml")

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
