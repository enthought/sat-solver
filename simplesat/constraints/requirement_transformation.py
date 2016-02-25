#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

from simplesat.constraints.kinds import (
    Any, EnpkgUpstreamMatch, Equal, Not, GEQ, GT, LEQ, LT,
)
from simplesat.constraints.requirement import Requirement


def Any_(_):
    return Any()

ALLOW_NEWER_MAP = {
    Any: Any_,
    Equal: GEQ,
    Not: Not,
    GEQ: GEQ,
    GT: GT,
    LEQ: Any_,
    LT: Any_,
    EnpkgUpstreamMatch: GEQ,
}

ALLOW_OLDER_MAP = {
    Any: Any_,
    Equal: LEQ,
    Not: Not,
    GEQ: Any_,
    GT: Any_,
    LEQ: LEQ,
    LT: LT,
    EnpkgUpstreamMatch: LEQ,
}

ALLOW_ANY_MAP = {
    Any: Any_,
    Equal: Any_,
    Not: Not,
    GEQ: Any_,
    GT: Any_,
    LEQ: Any_,
    LT: Any_,
    EnpkgUpstreamMatch: Any_,
}


def _transform_requirement(
        requirement, allow_newer=None, allow_any=None, allow_older=None):

    name = requirement.name
    original_constraints = constraints = requirement._constraints._constraints
    transformers = (
        (allow_older or set(), ALLOW_OLDER_MAP),
        (allow_newer or set(), ALLOW_NEWER_MAP),
        (allow_any or set(), ALLOW_ANY_MAP),
    )

    modified = False
    for names, type_map in transformers:
        if name in names:
            modified = True
            constraints = _transform_constraints(constraints, type_map)

    if modified and constraints != original_constraints:
        return TransformedRequirement(name, constraints, requirement)

    return requirement


def _transform_constraints(constraints, type_map):
    return tuple(
        type_map[type(c)](getattr(c, 'version', None))
        for c in constraints
    )


transform_install_requires = _transform_requirement  # noqa
transform_conflicts = _transform_requirement  # noqa


class TransformedRequirement(Requirement):

    def __init__(self, name, constraints, requirement):
        self._original_requirement = requirement
        super(TransformedRequirement, self).__init__(
            name, constraints=constraints)
