import unittest

from ..constraint_modifiers import ConstraintModifiers


class TestConstraintModifiers(unittest.TestCase):

    def test_initialization(self):
        # Given
        modifiers = ConstraintModifiers(allow_any='abc',
                                        allow_newer=('u', 'v'),
                                        allow_older=['x', 'y'])

        # Then
        self.assertEqual(modifiers.allow_any, set(('abc',)))
        self.assertEqual(modifiers.allow_newer, set(('u', 'v')))
        self.assertEqual(modifiers.allow_older, set(('x', 'y')))

    def test_asdict(self):
        # Given
        modifiers = ConstraintModifiers(allow_any=('c', 'b'),
                                        allow_newer=('z', 'a'),
                                        allow_older=['x', 'y'])

        # Then
        modifiers_dict = modifiers.asdict()
        expected_dict = {'allow_any': ['b', 'c'],
                         'allow_newer': ['a', 'z'],
                         'allow_older': ['x', 'y']}
        self.assertEqual(modifiers_dict, expected_dict)

    def test_update(self):
        # Given
        modifiers = ConstraintModifiers(allow_any=('a', 'b'))
        other_modifiers = ConstraintModifiers(allow_any='new',
                                              allow_newer=('u', 'v'))

        # Then
        modifiers.update(other_modifiers)
        self.assertEqual(modifiers.allow_any, set(('a', 'b', 'new')))
        self.assertEqual(modifiers.allow_newer, set(('u', 'v')))
        self.assertEqual(modifiers.allow_older, set())

    def test_targets(self):
        # Given
        modifiers = ConstraintModifiers(allow_any=('a', 'b', 'c'),
                                        allow_newer=('u', 'v'))

        # Then
        self.assertEqual(modifiers.targets, set(('a', 'b', 'c', 'u', 'v')))
