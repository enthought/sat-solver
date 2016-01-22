#!/usr/bin/env python
# -*- coding: utf-8 -*-


class SolverException(Exception):
    pass


class InvalidConstraint(SolverException):
    pass


class InvalidDependencyString(InvalidConstraint):
    pass


class NoPackageFound(SolverException):
    pass


class SatisfiabilityError(SolverException):
    def __init__(self, reason):
        super(SatisfiabilityError, self).__init__(None)
        self.reason = reason
