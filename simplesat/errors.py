#!/usr/bin/env python
# -*- coding: utf-8 -*-

from egginst.errors import SolverException


class InvalidDependencyString(SolverException):
    pass


class NoSuchPackage(SolverException):
    pass


class SatisfiabilityError(SolverException):
    def __init__(self, reason):
        super(SatisfiabilityError, self).__init__(None)
        self.reason = reason
