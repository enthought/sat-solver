"""
Simple data structures to hold SAT literals, clauses, etc.

"""


class Literal(object):

    def __init__(self, name, is_conjugated=False):
        self.name = name
        self.is_conjugated = is_conjugated

    def __str__(self):
        return '{}{}'.format('-' if self.is_conjugated else '', self.name)

    def __repr__(self):
        return "Literal('{}', is_conjugated={})".format(
            self.name, self.is_conjugated)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return (self.name == other.name and
                self.is_conjugated == other.is_conjugated)


class Clause(list):

    def __init__(self, *args):
        self.extend(args)

    @classmethod
    def from_string(cls, s):  # TODO Make this take Dimacs.
        # Very primitive variable parsing.
        self = cls()
        for raw in s.split():
            is_conjugated = raw[0] == '-'
            if is_conjugated:
                name = raw[1:]
            else:
                name = raw
            self.append(Literal(name, is_conjugated))
        return self

    def __str__(self):
        return ' '.join(str(lit) for lit in self)
