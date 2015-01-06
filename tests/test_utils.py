from unittest import TestCase

from simplesat.utils import Clause, Literal


class TestLiteral(TestCase):

    def test_equality(self):
        # Given
        lit1 = Literal('a', False)
        lit2 = Literal('a', False)
        lit3 = Literal('b', False)
        lit4 = Literal('b', True)

        # When/then
        self.assertEqual(lit1, lit2)
        self.assertNotEqual(lit2, lit3)
        self.assertNotEqual(lit3, lit4)


class TestClause(TestCase):

    def test_parse_clause(self):
        # Given
        clause = '-A B c'

        # When
        parsed = Clause.from_string(clause)

        # Then
        expected = [
            Literal('A', True), Literal('B', False), Literal('c', False)
        ]
        self.assertEqual(parsed, expected)
