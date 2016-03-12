import unittest

from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import PrettyPackageStringParser, InstallRequirement
from simplesat.dependency_solver import DependencySolver
from simplesat.pool import Pool
from simplesat.repository import Repository
from simplesat.request import Request
from simplesat.transaction import (
    InstallOperation, RemoveOperation, UpdateOperation
)


R = InstallRequirement._from_string


class TestSolver(unittest.TestCase):
    def setUp(self):
        self.repository = Repository()
        self.installed_repository = Repository()

        self._package_parser = PrettyPackageStringParser(
            EnpkgVersion.from_string
        )

    def package_factory(self, s):
        return self._package_parser.parse_to_package(s)

    def resolve(self, request):
        pool = Pool([self.repository, self.installed_repository])
        solver = DependencySolver(
            pool, self.repository, self.installed_repository, use_pruning=False
        )
        return solver.solve(request)

    def assertEqualOperations(self, operations, r_operations):
        self.assertEqual(operations, r_operations)

    def test_simple_install(self):
        # Given
        mkl = self.package_factory(u"mkl 10.3-1")
        self.repository.add_package(mkl)

        r_operations = [InstallOperation(mkl)]

        request = Request()
        request.install(R("mkl"))

        # When
        transaction = self.resolve(request)

        # Then
        self.assertEqualOperations(transaction.operations, r_operations)

    def test_multiple_installs(self):
        # Given
        mkl = self.package_factory(u"mkl 10.3-1")
        libgfortran = self.package_factory(u"libgfortran 3.0.0-2")

        r_operations = [
            InstallOperation(libgfortran),
            InstallOperation(mkl),
        ]

        self.repository.add_package(mkl)
        self.repository.add_package(libgfortran)

        request = Request()
        request.install(R("mkl"))
        request.install(R("libgfortran"))

        # When
        transaction = self.resolve(request)

        # Then
        self.assertEqualOperations(transaction.operations, r_operations)

    def test_simple_dependency(self):
        # Given
        mkl = self.package_factory(u"mkl 10.3-1")
        libgfortran = self.package_factory(u"libgfortran 3.0.0-2")
        numpy = self.package_factory(
            u"numpy 1.9.2-1; depends (mkl == 10.3-1, libgfortran ^= 3.0.0)"
        )

        r_operations = [
            # libgfortran sorts before mkl
            InstallOperation(libgfortran),
            InstallOperation(mkl),
            InstallOperation(numpy),
        ]

        self.repository.add_package(mkl)
        self.repository.add_package(libgfortran)
        self.repository.add_package(numpy)

        request = Request()
        request.install(R("numpy"))

        # When
        transaction = self.resolve(request)

        # Then
        self.assertEqualOperations(transaction.operations, r_operations)

    def test_already_installed(self):
        # Given
        mkl1 = self.package_factory(u"mkl 10.3-1")
        mkl2 = self.package_factory(u"mkl 10.3-2")

        r_operations = []

        self.repository.add_package(mkl1)
        self.repository.add_package(mkl2)
        self.installed_repository.add_package(mkl1)

        # When
        request = Request()
        request.install(R("mkl"))

        transaction = self.resolve(request)

        # Then
        self.assertEqualOperations(transaction.operations, r_operations)

        # Given
        r_operations = [
            RemoveOperation(mkl1),
            InstallOperation(mkl2),
        ]
        r_pretty_operations = [
            UpdateOperation(mkl2, mkl1),
        ]

        # When
        request = Request()
        request.install(R("mkl > 10.3-1"))

        # When
        transaction = self.resolve(request)

        # Then
        self.assertEqualOperations(transaction.operations, r_operations)
        self.assertEqualOperations(
            transaction.pretty_operations, r_pretty_operations)
