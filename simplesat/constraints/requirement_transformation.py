#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

from collections import OrderedDict

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
        (allow_older or (), ALLOW_OLDER_MAP),
        (allow_newer or (), ALLOW_NEWER_MAP),
        (allow_any or (), ALLOW_ANY_MAP),
    )

    modified = False
    for names, type_map in transformers:
        if name in names:
            modified = True
            constraints = _transform_constraints(constraints, type_map)

    if modified and constraints != original_constraints:
        # Remove duplicate constraints
        constraints = tuple(OrderedDict.fromkeys(constraints).keys())
        return TransformedRequirement(name, constraints, requirement)

    return requirement


def _transform_constraints(constraints, type_map):
    return tuple(
        type_map[type(c)](getattr(c, 'version', None))
        for c in constraints
    )


class _TransformInstallRequires(object):

    @staticmethod
    def __call__(*a, **kw):
        return _transform_requirement(*a, **kw)

    @staticmethod
    def from_modifiers(constraints, modifiers):
        return _transform_requirement(
            constraints,
            allow_newer=modifiers.allow_newer,
            allow_older=modifiers.allow_older,
            allow_any=modifiers.allow_any
        )


class _TransformConflicts(_TransformInstallRequires):
    pass


transform_install_requires = _TransformInstallRequires()
transform_constraints = _TransformConflicts()


class TransformedRequirement(Requirement):

    def __init__(self, name, constraints, requirement):
        self._original_requirement = requirement
        super(TransformedRequirement, self).__init__(
            name, constraints=constraints)
