#!/usr/bin/env python
# -*- coding: utf-8 -*-


class SolverException(Exception):
    pass


class InvalidConstraint(SolverException):
    pass


class InvalidDependencyString(InvalidConstraint):
    pass


class NoPackageFound(SolverException):
    def __init__(self, requirement, *a, **kw):
        # NOTE: Working around a circular import
        from simplesat.constraints.requirement import Requirement

        if not isinstance(requirement, Requirement):
            msg = "NoPackageFound expects a Requirement as first arg. Got {!r}"
            raise TypeError(msg.format(requirement))
        super(NoPackageFound, self).__init__(*a, **kw)
        self.requirement = requirement
        self.args = self.args or (str(requirement),)


class MissingInstallRequires(NoPackageFound):
    pass


class MissingConflicts(NoPackageFound):
    pass


class SatisfiabilityError(SolverException):
    def __init__(self, unsat):
        self.unsat = unsat
        super(SatisfiabilityError, self).__init__(self.reason)

    @property
    def reason(self):
        return self.unsat.to_string()
