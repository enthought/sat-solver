#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

from collections import OrderedDict

from attr import attr, attributes, asdict
from attr.validators import instance_of
import six

from okonomiyaki.versions import EnpkgVersion
from simplesat.constraints.kinds import (
    Any, EnpkgUpstreamMatch, Equal, Not, GEQ, GT, LEQ, LT,
)
from simplesat.constraints.requirement import Requirement


MAX_BUILD = 999999999  # Nine nines... I guess


def Any_(_version):
    # This just eats the 'version' argument
    return Any()


def LEQ_LEAST_UPPER_BOUND(version):
    new_version = EnpkgVersion.from_upstream_and_build(
        str(version.upstream), MAX_BUILD)
    return LEQ(new_version)


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
    EnpkgUpstreamMatch: LEQ_LEAST_UPPER_BOUND,
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


def iterable_to_set(container):
    """ Return a set from an iterable, being careful not to disassemble
    strings.
        >>> iterable_to_set(['foo'])
        set(['foo'])
        >>> iterable_to_set('foo')
        set(['foo'])
    """
    if isinstance(container, six.string_types):
        container = (container,)
    return set(container)


_defaults = dict(default=(), convert=iterable_to_set,
                 validator=instance_of(set))


@attributes
class ConstraintModifiers(object):
    allow_newer = attr(**_defaults)
    allow_any = attr(**_defaults)
    allow_older = attr(**_defaults)

    def asdict(self):
        return asdict(self)

    @property
    def targets(self):
        return set.union(self.allow_newer, self.allow_any, self.allow_older)


def _transform_requirement(
        requirement, allow_newer=None, allow_any=None, allow_older=None):
    """If any of the modifier rules apply, return a new Requirement with
    modified constraints, otherwise return the original requirement.
    """

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
        return Requirement(name, constraints)

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
    def with_modifiers(constraints, modifiers):
        return _transform_requirement(
            constraints,
            allow_newer=modifiers.allow_newer,
            allow_older=modifiers.allow_older,
            allow_any=modifiers.allow_any
        )


class _TransformConflicts(_TransformInstallRequires):
    pass


transform_install_requires = _TransformInstallRequires()
transform_conflicts = _TransformConflicts()
