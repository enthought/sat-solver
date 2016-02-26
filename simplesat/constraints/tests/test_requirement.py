import unittest
from collections import OrderedDict

from okonomiyaki.versions import EnpkgVersion

from simplesat.errors import (
    InvalidConstraint, InvalidDependencyString, SolverException
)

from ..kinds import Equal
from ..multi import MultiConstraints
from ..parser import _RawConstraintsParser
from ..requirement import Requirement, parse_package_full_name
from ..requirement_transformation import (
    ALLOW_ANY_MAP, transform_install_requires, _transform_constraints
)


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
            Requirement.from_constraints(("numpy", (("*",),)))
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
            (("numpy", (("*",),)), False),
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
        r_requirement = Requirement.from_constraints(("numpy", (("*",),)))
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


class TestRequirementTransformation(unittest.TestCase):

    name = "MKL"
    not_name = "shapely"
    never_name = "basemap"

    def run_transformations(self, constraints, transform, allow):

        self.assertSingleMulti(
            constraints, self.name, transform_install_requires, allow)

        # When
        noop_constraints = tuple(
            (before, before)
            for before, _ in constraints
        )

        # Then
        self.assertSingleMulti(
            noop_constraints, self.not_name, transform, allow)

    def assertSingleMulti(self, constraints, name, transform, allow):
        # When single-constraint per requirement
        requirement_strings = self._add_name(name, constraints)

        # Then
        self.assertTransformations(
            requirement_strings,
            transform,
            **allow)

        # When the constraints are all together as a single requirement
        before = ', '.join(dict(requirement_strings).keys())
        after = ', '.join(self._nub(dict(requirement_strings).values()))
        requirement_strings = ((before, after),)

        # Then
        self.assertTransformations(
            requirement_strings,
            transform,
            **allow)

    def assertTransformations(self, requirement_strings, transform, **kw):
        # Given
        R = Requirement._from_string
        for before, after in requirement_strings:
            # When
            req = R(before)
            result = transform(req, **kw)
            expected = R(after)

            # Then
            self.assertEqual(expected, result)

    def _add_name(self, name, pairs):
        return tuple(
            (name + ' ' + before, name + ' ' + after)
            for before, after in pairs)

    def _nub(self, sequence):
        return tuple(OrderedDict.fromkeys(sequence).keys())

    def test_allow_newer(self):
        # Given
        constraints = (
            ("*", "*"),
            ("> 1.1.1-1", "> 1.1.1-1"),
            (">= 1.1.1-1", ">= 1.1.1-1"),
            ("< 1.1.1-1", "*"),
            ("<= 1.1.1-1", "*"),
            ("^= 1.1.1", ">= 1.1.1"),
            ("== 1.1.1-1", ">= 1.1.1-1"),
            ("!= 1.1.1-1", "!= 1.1.1-1"),
        )

        # When
        allow = {'allow_newer': set([self.name])}

        # Then
        self.run_transformations(
            constraints, transform_install_requires, allow)

    def test_allow_older(self):
        # Given
        constraints = (
            ("*", "*"),
            ("> 1.1.1-1", "*"),
            (">= 1.1.1-1", "*"),
            ("< 1.1.1-1", "< 1.1.1-1"),
            ("<= 1.1.1-1", "<= 1.1.1-1"),
            ("^= 1.1.1", "<= 1.1.1"),
            ("== 1.1.1-1", "<= 1.1.1-1"),
            ("!= 1.1.1-1", "!= 1.1.1-1"),
        )

        # When
        allow = {'allow_older': set([self.name]),
                 'allow_newer': set([self.never_name])}

        # Then
        self.run_transformations(
            constraints, transform_install_requires, allow)

    def test_allow_any(self):
        # Given
        constraints = (
            ("*", "*"),
            ("> 1.1.1-1", "*"),
            (">= 1.1.1-1", "*"),
            ("< 1.1.1-1", "*"),
            ("<= 1.1.1-1", "*"),
            ("^= 1.1.1", "*"),
            ("== 1.1.1-1", "*"),
            ("!= 1.1.1-1", "!= 1.1.1-1"),
        )

        # When
        allow = {'allow_any': set([self.name]),
                 'allow_older': set([self.never_name])}

        # Then
        self.run_transformations(
            constraints, transform_install_requires, allow)

    def test_newer_older_is_any(self):
        # Given
        constraints = (
            "*",
            "> 1.1.1-1",
            ">= 1.1.1-1",
            "< 1.1.1-1",
            "<= 1.1.1-1",
            "^= 1.1.1",
            "== 1.1.1-1",
            "!= 1.1.1-1",
        )
        constraint_objs = _RawConstraintsParser().parse(
            ', '.join(constraints), EnpkgVersion.from_string)
        any_constraints = zip(
            constraints,
            map(str, _transform_constraints(constraint_objs, ALLOW_ANY_MAP))
        )

        # When
        allow = {'allow_older': set([self.name]),
                 'allow_newer': set([self.name])}

        # Then
        self.run_transformations(
            any_constraints, transform_install_requires, allow)

    def test_collapse_multiple_any(self):
        # Given
        requirement = Requirement._from_string(
            "MKL >= 1.2.1-2, MKL != 2.3.1-1, MKL < 1.4"
        )
        expected = Requirement._from_string(
            "MKL, MKL != 2.3.1-1"
        )

        # When
        transformed = transform_install_requires(
            requirement, allow_any=set(["MKL"]))
        constraints = transformed._constraints._constraints

        # Then
        self.assertEqual(2, len(constraints))
        self.assertEqual(expected, transformed)
