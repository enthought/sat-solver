import sys
import unittest

import six

from okonomiyaki.platforms import PythonImplementation
from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints.kinds import Equal
from simplesat.constraints.package_parser import (
    PrettyPackageStringParser, legacy_dependencies_to_pretty_string,
    package_to_pretty_string
)
from simplesat.errors import SolverException
from simplesat.package import PackageMetadata


RUNNING_PYTHON = PythonImplementation(
    "cp", sys.version_info[0], sys.version_info[1]
)

V = EnpkgVersion.from_string


class TestPrettyPackageStringParser(unittest.TestCase):
    def test_invalid_formats(self):
        # Given
        parser = PrettyPackageStringParser(V)
        package_string = ""
        r_message = "Invalid preamble: "

        # When
        with self.assertRaisesRegexp(ValueError, r_message):
            parser.parse(package_string)

        # Given
        package_string = "numpy"
        r_message = "Invalid preamble: 'numpy'"

        # When
        with self.assertRaisesRegexp(ValueError, r_message):
            parser.parse(package_string)

        # Given
        package_string = "numpy 1.8.0-1; depends (nose 1.3.2)"
        r_message = "Invalid requirement block: "

        # When
        with self.assertRaisesRegexp(SolverException, r_message):
            parser.parse(package_string)

        # Given
        package_string = "numpy 1.8.0-1; conflicts (nose 1.3.2)"
        r_message = "Invalid constraint block: 'conflicts \(nose 1.3.2\)'"

        # When
        with self.assertRaisesRegexp(ValueError, r_message):
            parser.parse(package_string)

    def test_simple(self):
        # Given
        parser = PrettyPackageStringParser(V)
        package_string = "numpy 1.8.0-1; depends (nose == 1.3.4-1)"

        # When
        name, version, constraints = parser.parse(package_string)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertTrue("nose" in constraints)
        self.assertEqual(constraints["nose"], set((Equal(V("1.3.4-1")),)))

    def test_no_dependencies(self):
        # Given
        parser = PrettyPackageStringParser(V)
        package_string = "numpy 1.8.0-1"

        # When
        name, version, constraints = parser.parse(package_string)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        six.assertCountEqual(self, constraints, set())

    def test_to_legacy_constraints(self):
        # Given
        parser = PrettyPackageStringParser(V)
        package_string = "numpy 1.8.0-1; depends (nose == 1.3.4-1)"

        # When
        name, version, constraints = parser.parse_to_legacy_constraints(package_string)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertEqual(constraints, ("nose 1.3.4-1",))

        # Given
        package_string = "numpy 1.8.0-1; depends (nose ~= 1.3.4)"

        # When
        name, version, constraints = parser.parse_to_legacy_constraints(package_string)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertEqual(constraints, ("nose 1.3.4",))

        # Given
        package_string = "numpy 1.8.0-1; depends (nose)"

        # When
        name, version, constraints = parser.parse_to_legacy_constraints(package_string)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertEqual(constraints, ("nose",))


class TestLegacyDependenciesToPrettyString(unittest.TestCase):
    def test_simple(self):
        # Given
        dependencies = ["MKL 10.3-1", "nose 1.3.4"]
        r_pretty_string = "MKL == 10.3-1, nose ~= 1.3.4"

        # When
        pretty_string = legacy_dependencies_to_pretty_string(dependencies)

        # Then
        self.assertEqual(pretty_string, r_pretty_string)


class TestPackagePrettyString(unittest.TestCase):
    def test_simple(self):
        # Given
        package = PackageMetadata(u"numpy", V("1.8.1-1"), ("MKL 10.3-1",))

        r_pretty_string = u"numpy 1.8.1-1; depends (MKL == 10.3-1)"

        # When
        pretty_string = package_to_pretty_string(package)

        # Then
        self.assertEqual(pretty_string, r_pretty_string)

        # Given
        key = "numpy-1.8.1-1.egg"
        package = PackageMetadata(u"numpy", V("1.8.1-1"), ("nose",))

        r_pretty_string = "numpy 1.8.1-1; depends (nose)"

        # When
        pretty_string = package_to_pretty_string(package)

        # Then
        self.assertEqual(pretty_string, r_pretty_string)


class TestToPackage(unittest.TestCase):
    def test_simple(self):
        # Given
        s = u"numpy 1.8.1; depends (MKL ~= 10.3)"
        parser = PrettyPackageStringParser(EnpkgVersion.from_string)

        # When
        package = parser.parse_to_package(s)

        # Then
        self.assertEqual(package.name, "numpy")
        self.assertEqual(package.dependencies, ("MKL 10.3",))
