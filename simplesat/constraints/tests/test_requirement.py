import unittest

from okonomiyaki.versions import EnpkgVersion

from simplesat.errors import (
    InvalidConstraint, InvalidDependencyString, SolverException
)

from ..kinds import Equal
from ..multi import MultiConstraints
from ..requirement import Requirement, parse_package_full_name


V = EnpkgVersion.from_string


class TestRequirementFromConstraint(unittest.TestCase):
    def test_comparison(self):
        # Given
        constraints0 = ("numpy", ((">= 1.8.1-3", "< 1.9.0"),))
        constraints1 = ("numpy", ((">= 1.8.1-3", "< 1.9.1"),))

        # When
        requirement0 = Requirement.from_constraints(constraints0)
        requirement1 = Requirement.from_constraints(constraints1)

        # Then
        self.assertTrue(requirement0 != requirement1)

    def test_hashing(self):
        # Given
        constraints0 = ("numpy", ((">= 1.8.1-3", "< 1.9.1"),))

        # When
        requirement0 = Requirement.from_constraints(constraints0)
        requirement1 = Requirement.from_constraints(constraints0)

        # Then
        self.assertEqual(requirement0, requirement1)
        self.assertEqual(hash(requirement0), hash(requirement1))

    def test_any(self):
        # Given
        constraints0 = ("numpy", ((),))

        # When
        requirement = Requirement.from_constraints(constraints0)

        # Then
        self.assertTrue(requirement.matches(V("1.8.1-2")))
        self.assertTrue(requirement.matches(V("1.8.1-3")))
        self.assertTrue(requirement.matches(V("1.8.2-1")))
        self.assertTrue(requirement.matches(V("1.9.0-1")))
        self.assertEqual(
            requirement,
            Requirement.from_constraints(("numpy", (("*"),)))
        )

    def test_simple(self):
        # Given
        constraints0 = ("numpy", ((">= 1.8.1-3", "< 1.9.0"),))

        # When
        requirement = Requirement.from_constraints(constraints0)

        # Then
        self.assertFalse(requirement.matches(V("1.8.1-2")))
        self.assertTrue(requirement.matches(V("1.8.1-3")))
        self.assertTrue(requirement.matches(V("1.8.2-1")))
        self.assertFalse(requirement.matches(V("1.9.0-1")))

    def test_multiple_fails(self):
        # Given
        constraints0 = (("numpy", ((">= 1.8.1-3",),)),
                        ("scipy", (("< 1.9.0",),)))

        # Then
        with self.assertRaises(InvalidConstraint):
            Requirement.from_constraints(constraints0)

    def test_disjunction_fails(self):
        constraints0 = ("numpy", (("< 1.8.0",), (">= 1.8.1-3",)))

        # Then
        with self.assertRaises(InvalidConstraint):
            Requirement.from_constraints(constraints0)

    def test_has_any_version_constraint(self):
        # Given
        requirements = [
            (("numpy", ((),)), False),
            (("numpy", (("< 1.8.1",),)), True),
            (("numpy", (("== 1.8.1-1",),)), True),
            (("numpy", (("^= 1.8.1",),)), True),
        ]

        # When/Then
        for pretty_string, has_any_version_constraint in requirements:
            requirement = Requirement.from_constraints(pretty_string)
            self.assertEqual(
                requirement.has_any_version_constraint,
                has_any_version_constraint
            )


class TestRequirementFromString(unittest.TestCase):
    def test_comparison(self):
        # Given
        requirement_string1 = "numpy >= 1.8.1-3, numpy < 1.9.0"
        requirement_string2 = "numpy >= 1.8.1-3, numpy < 1.9.1"

        # When
        requirement1 = Requirement._from_string(requirement_string1)
        requirement2 = Requirement._from_string(requirement_string2)

        # Then
        self.assertTrue(requirement1 != requirement2)

    def test_hashing(self):
        # Given
        requirement_string = "numpy >= 1.8.1-3, numpy < 1.9.0"

        # When
        requirement1 = Requirement._from_string(requirement_string)
        requirement2 = Requirement._from_string(requirement_string)

        # Then
        self.assertEqual(requirement1, requirement2)
        self.assertEqual(hash(requirement1), hash(requirement2))

    def test_any(self):
        # Given
        requirement_string = "numpy"
        r_requirement = Requirement.from_constraints(("numpy", (("*"),)))
        r_requirement_empty = Requirement.from_constraints(("numpy", ((),)))

        # When
        requirement = Requirement._from_string(requirement_string)

        # Then
        self.assertTrue(requirement.matches(V("1.8.1-2")))
        self.assertTrue(requirement.matches(V("1.8.1-3")))
        self.assertTrue(requirement.matches(V("1.8.2-1")))
        self.assertTrue(requirement.matches(V("1.9.0-1")))
        self.assertEqual(requirement, r_requirement)
        self.assertEqual(requirement, r_requirement_empty)
        self.assertEqual(r_requirement, r_requirement_empty)

        # Given
        requirement_string = "numpy *"

        # When
        requirement = Requirement._from_string(requirement_string)

        # Then
        self.assertEqual(requirement, r_requirement)
        self.assertEqual(requirement, r_requirement_empty)
        self.assertEqual(r_requirement, r_requirement_empty)

    def test_simple(self):
        # Given
        requirement_string = "numpy >= 1.8.1-3, numpy < 1.9.0"

        # When
        requirement = Requirement._from_string(requirement_string)

        # Then
        self.assertFalse(requirement.matches(V("1.8.1-2")))
        self.assertTrue(requirement.matches(V("1.8.1-3")))
        self.assertTrue(requirement.matches(V("1.8.2-1")))
        self.assertFalse(requirement.matches(V("1.9.0-1")))

    def test_multiple_fails(self):
        # Given
        requirement_string = "numpy >= 1.8.1-3, scipy < 1.9.0"

        # When
        with self.assertRaises(InvalidDependencyString):
            Requirement._from_string(requirement_string)

    def test_from_package_string(self):
        # Given
        package_s = "numpy-1.8.1-1"

        # When
        requirement = Requirement.from_package_string(package_s)

        # Then
        self.assertEqual(requirement.name, "numpy")
        self.assertEqual(requirement._constraints,
                         MultiConstraints([Equal(V("1.8.1-1"))]))

    def test_has_any_version_constraint(self):
        # Given
        requirements = [
            ("numpy", False),
            ("numpy < 1.8.1", True),
            ("numpy == 1.8.1-1", True),
            ("numpy ^= 1.8.1", True),
        ]

        # When/Then
        for pretty_string, has_any_version_constraint in requirements:
            requirement = Requirement._from_string(pretty_string)
            self.assertEqual(
                requirement.has_any_version_constraint,
                has_any_version_constraint
            )


class TestParsePackageFullName(unittest.TestCase):
    def test_simple(self):
        # Given
        package_s = "numpy-1.8.1-1"

        # When
        name, version = parse_package_full_name(package_s)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, "1.8.1-1")

        # Given
        package_s = "numpy 1.8.1"

        # When/Then
        with self.assertRaises(SolverException):
            parse_package_full_name(package_s)


class TestRequirement(unittest.TestCase):
    def test_repr(self):
        # Given
        constraints = (
            "numpy", (("^= 1.8.0",),)
        )
        r_repr = "Requirement('numpy ^= 1.8.0')"

        # When
        requirement = Requirement.from_constraints(constraints)

        # Then
        self.assertMultiLineEqual(repr(requirement), r_repr)

        # Given
        constraints = (
            "numpy", ((">= 1.8.0", "< 1.10.0"),)
        )
        r_repr = "Requirement('numpy >= 1.8.0-0, < 1.10.0-0')"

        # When
        requirement = Requirement.from_constraints(constraints)

        # Then
        self.assertMultiLineEqual(repr(requirement), r_repr)

        # Given
        constraints = (
            "numpy", ((">= 1.8.0-0", "< 1.10.0-0"),)
        )
        r_repr = "Requirement('numpy >= 1.8.0-0, < 1.10.0-0')"

        # When
        requirement = Requirement.from_constraints(constraints)

        # Then
        self.assertMultiLineEqual(repr(requirement), r_repr)
