import textwrap
import unittest

from simplesat.constraints import ConstraintModifiers, Requirement
from simplesat.errors import NoPackageFound
from simplesat.test_utils import packages_from_definition

from ..dependency_solver import requirements_are_satisfiable


class TestRequirementsAreSatistifiable(unittest.TestCase):
    def test_simple(self):
        # Given
        packages_definition = textwrap.dedent("""\
        MKL 10.3-1
        MKL 11.4.1-1
        numpy 1.9.2-1; depends (MKL == 10.3-1)
        numpy 1.10.4-1; depends (MKL == 11.4.1-1)"""
        )
        packages = packages_from_definition(packages_definition)

        # When/Then
        requirements = [Requirement._from_string("numpy")]
        self.assertTrue(requirements_are_satisfiable(packages,  requirements))

        # When/Then
        requirements = [Requirement._from_string("numpy < 1.10")]
        self.assertTrue(requirements_are_satisfiable(packages,  requirements))

        # When/Then
        requirements = [
            Requirement._from_string("numpy < 1.10"),
            Requirement._from_string("MKL >= 11")
        ]
        self.assertFalse(requirements_are_satisfiable(packages,  requirements))

        # When/Then
        requirements = [
            Requirement._from_string("numpy > 1.10"),
            Requirement._from_string("MKL >= 11")
        ]
        self.assertTrue(requirements_are_satisfiable(packages,  requirements))

    def test_raises_if_unresolvable_requirement(self):
        # Given
        packages_definition = textwrap.dedent("""\
        MKL 11.4.1-1;
        numpy 1.10.4-1; depends (MKL == 11.4.1-1)"""
        )
        packages = packages_from_definition(packages_definition)

        requirements = [Requirement._from_string("foo")]

        # When/Then
        with self.assertRaises(NoPackageFound):
            requirements_are_satisfiable(packages,  requirements)

    def test_constraint_modifiers(self):
        # Given
        packages_definition = textwrap.dedent("""\
        MKL 10.3-1
        MKL 11.4.1-1
        numpy 1.9.2-1; depends (MKL == 10.3-1)
        numpy 1.10.4-1; depends (MKL == 11.4.1-1)"""
        )
        packages = packages_from_definition(packages_definition)

        requirements = [
            Requirement._from_string("numpy < 1.10"),
            Requirement._from_string("MKL >= 11")
        ]
        modifiers = ConstraintModifiers(allow_newer=("MKL",))

        # When/Then
        self.assertFalse(requirements_are_satisfiable(packages, requirements))
        self.assertTrue(
            requirements_are_satisfiable(packages, requirements, modifiers)
        )
