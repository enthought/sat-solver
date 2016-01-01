import collections
import re

from simplesat.constraints.kinds import (
    Any, EnpkgUpstreamMatch, Equal, GEQ, GT, LEQ, LT, Not
)

from simplesat.errors import SolverException


_VERSION_R = "[^=><!,\s~][^,\s]+"
_EQUAL_R = "=="
_GEQ_R = ">="
_GT_R = r">"
_LEQ_R = r"<="
_LT_R = r"<"
_NOT_R = r"!="
_ENPKG_UPSTREAM_MATCH_R = r"~="
_ANY_R = r"\*"
_WS_R = " +"

_CONSTRAINTS_SCANNER = re.Scanner([
    (_VERSION_R, lambda scanner, token: VersionToken(token)),
    (_EQUAL_R, lambda scanner, token: EqualToken(token)),
    (_GEQ_R, lambda scanner, token: GEQToken(token)),
    (_GT_R, lambda scanner, token: GTToken(token)),
    (_LEQ_R, lambda scanner, token: LEQToken(token)),
    (_LT_R, lambda scanner, token: LTToken(token)),
    (_NOT_R, lambda scanner, token: NotToken(token)),
    (_ENPKG_UPSTREAM_MATCH_R,
        lambda scanner, token: EnpkgUpstreamMatchToken(token)),
    (_ANY_R, lambda scanner, token: AnyToken(token)),
    (_WS_R, lambda scanner, token: None),
])

_DISTRIBUTION_R = "[a-zA-Z_][^\s-]*"

_REQUIREMENTS_SCANNER = re.Scanner([
    (_DISTRIBUTION_R, lambda scanner, token: DistributionNameToken(token)),
    (_VERSION_R, lambda scanner, token: VersionToken(token)),
    (_EQUAL_R, lambda scanner, token: EqualToken(token)),
    (_GEQ_R, lambda scanner, token: GEQToken(token)),
    (_GT_R, lambda scanner, token: GTToken(token)),
    (_LEQ_R, lambda scanner, token: LEQToken(token)),
    (_LT_R, lambda scanner, token: LTToken(token)),
    (_NOT_R, lambda scanner, token: NotToken(token)),
    (_ENPKG_UPSTREAM_MATCH_R,
        lambda scanner, token: EnpkgUpstreamMatchToken(token)),
    (_ANY_R, lambda scanner, token: AnyToken(token)),
    (_WS_R, lambda scanner, token: None),
])


class Token(object):
    kind = None

    def __init__(self, value=None):
        self.value = value


class CommaToken(Token):
    kind = "comma"


class DistributionNameToken(Token):
    kind = "distribution_name"


class AnyToken(Token):
    kind = "any"


class VersionToken(Token):
    kind = "version"


class ComparisonToken(Token):
    kind = "comparison"


class LEQToken(ComparisonToken):
    kind = "leq"


class LTToken(ComparisonToken):
    kind = "lt"


class GEQToken(ComparisonToken):
    kind = "geq"


class GTToken(ComparisonToken):
    kind = "gt"


class EnpkgUpstreamMatchToken(ComparisonToken):
    kind = "enpkg_upstream"


class EqualToken(ComparisonToken):
    kind = "equal"


class NotToken(ComparisonToken):
    kind = "not"


_OPERATOR_TO_SPEC = {
    EnpkgUpstreamMatchToken: EnpkgUpstreamMatch,
    EqualToken: Equal,
    GEQToken: GEQ,
    GTToken: GT,
    LEQToken: LEQ,
    LTToken: LT,
    NotToken: Not,
}


def _spec_factory(comparison_token):
    klass = _OPERATOR_TO_SPEC.get(comparison_token.__class__, None)
    if klass is None:
        msg = "Unsupported comparison token {0!r}".format(comparison_token)
        raise SolverException(msg)
    else:
        return klass


def _tokenize(scanner, requirement_string):
    tokens = []

    parts = requirement_string.split(",")
    for part in parts:
        scanned, remaining = scanner.scan(part.strip())
        if len(remaining) > 0:
            msg = "Invalid requirement string: {0!r}".  format(requirement_string)
            raise SolverException(msg)
        elif len(scanned) > 0:
            tokens.append(scanned)
    return tokens


def _operator_factory(operator, version, version_factory):
    operator = _spec_factory(operator)
    version = version_factory(version.value)
    return operator(version)


class _RawConstraintsParser(object):
    """A simple parser for requirement strings."""
    def __init__(self):
        self._scanner = _CONSTRAINTS_SCANNER

    def parse(self, requirement_string, version_factory):
        def add_constraint(constraints, requirement_block):
            if len(requirement_block) == 2:
                operator, version = requirement_block
                constraints.add(_operator_factory(operator, version,
                                                  version_factory))
            else:
                msg = ("Invalid requirement string: {0!r}".
                       format(requirement_string))
                raise SolverException(msg)

        constraints = set()
        tokens_blocks = _tokenize(self._scanner, requirement_string)

        for requirement_block in tokens_blocks:
            add_constraint(constraints, requirement_block)

        return constraints


class _RawRequirementParser(object):
    """A simple parser for requirement strings."""
    def __init__(self):
        self._scanner = _REQUIREMENTS_SCANNER

    def parse(self, requirement_string, version_factory):
        def add_constraint(constraints, requirement_block):
            if len(requirement_block) == 3:
                distribution, operator, version = requirement_block
                name = distribution.value
                constraints[name].add(_operator_factory(operator, version,
                                                        version_factory))
            elif len(requirement_block) == 1:
                name = requirement_block[0].value
                # Force name to exist in constraints
                constraints[name].add(Any())
            else:
                msg = ("Invalid requirement block: {0!r}".
                       format(requirement_block))
                raise SolverException(msg)

        constraints = collections.defaultdict(set)
        tokens_blocks = _tokenize(self._scanner, requirement_string)

        for requirement_block in tokens_blocks:
            add_constraint(constraints, requirement_block)

        return constraints
