#!/usr/bin/env python
# -*- coding: utf-8 -*-


class SolverException(Exception):
    pass


class InvalidConstraint(SolverException):
    pass


class InvalidDependencyString(InvalidConstraint):
    pass


class NoPackageFound(SolverException):
    def __init__(self, message, requirement, *a, **kw):
        super(NoPackageFound, self).__init__(message, requirement, *a, **kw)


class SatisfiabilityError(SolverException):
    def __init__(self, unsat):
        self.unsat = unsat
        super(SatisfiabilityError, self).__init__(self.reason)

    @property
    def reason(self):
        return self.unsat.to_string()
