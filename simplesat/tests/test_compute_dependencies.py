import unittest
from textwrap import dedent

from simplesat.constraints import InstallRequirement
from simplesat.package import PackageMetadata
from simplesat.test_utils import pool_and_repository_from_packages

from ..compute_dependencies import (compute_dependencies,
                                    compute_reverse_dependencies)


PACKAGE_DEF = dedent("""\
    A 0.0.0-1; depends (B ^= 0.0.0)
    B 0.0.0-1; depends (D == 0.0.0-2)
    B 0.0.0-2; depends (D ^= 0.0.0)
    C 0.0.0-1; depends (E ^= 1.0.0-1)
    D 0.0.0-2
    E 1.0.0-1
""")


class TestComputeDependencies(unittest.TestCase):

    def setUp(self):
        self.pool, self.repo = pool_and_repository_from_packages(PACKAGE_DEF)

    def _package_set_from_string(self, *package_strings):
        packages = set()
        for package_str in package_strings:
            packages.add(PackageMetadata._from_pretty_string(package_str))

        return packages

    def test_no_dependency(self):
        requirement = InstallRequirement._from_string('D == 0.0.0-2')
        expected_deps = set()
        deps = compute_dependencies(self.pool, requirement)
        self.assertEqual(deps, expected_deps)

    def test_simple_dependency(self):
        requirement = InstallRequirement._from_string('C ^= 0.0.0')
        expected_deps = self._package_set_from_string(
            'E 1.0.0-1'
        )
        deps = compute_dependencies(self.pool, requirement)
        self.assertEqual(deps, expected_deps)

    def test_multiple_satisfying_requirements(self):
        requirement = InstallRequirement._from_string('A ^= 0.0.0')
        expected_deps = self._package_set_from_string(
            'B 0.0.0-1; depends (D == 0.0.0-2)',
            'B 0.0.0-2; depends (D ^= 0.0.0)',
            'D 0.0.0-2'
        )

        deps = compute_dependencies(self.pool, requirement)
        self.assertEqual(deps, expected_deps)


class TestComputeReverseDependencies(unittest.TestCase):

    def setUp(self):
        self.pool, self.repo = pool_and_repository_from_packages(PACKAGE_DEF)

    def _package_set_from_string(self, *package_strings):
        packages = set()
        for package_str in package_strings:
            packages.add(PackageMetadata._from_pretty_string(package_str))

        return packages

    def test_no_dependency(self):
        requirement = InstallRequirement._from_string('A ^= 0.0.0')

        deps = compute_reverse_dependencies(self.pool, requirement)
        self.assertEqual(deps, set())

    def test_multiple_rev_dependencies(self):
        requirement = InstallRequirement._from_string('D ^= 0.0.0')
        expected_deps = self._package_set_from_string(
            'A 0.0.0-1; depends (B ^= 0.0.0)',
            'B 0.0.0-1; depends (D == 0.0.0-2)',
            'B 0.0.0-2; depends (D ^= 0.0.0)',
        )

        deps = compute_reverse_dependencies(self.pool, requirement)
        self.assertEqual(deps, expected_deps)
