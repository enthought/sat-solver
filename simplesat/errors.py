#!/usr/bin/env python
# -*- coding: utf-8 -*-

from egginst.errors import SolverException


class InvalidDependencyString(SolverException):
    pass


class SatisfiabilityError(SolverException):
    def __init__(self, unsat):
        reason = unsat.to_string()
        self.reason = reason
        self.unsat = unsat
        super(SatisfiabilityError, self).__init__(reason)
