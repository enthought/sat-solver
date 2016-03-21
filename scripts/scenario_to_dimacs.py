#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import json
import logging
import subprocess
import sys


from simplesat.dependency_solver import (
    DependencySolver, _connected_packages
)
from simplesat.pool import Pool
from simplesat.sat.policy import InstalledFirstPolicy
from simplesat.sat import MiniSATSolver
from simplesat.test_utils import Scenario
from simplesat.transaction import Transaction


def clauses_to_dimacs(clauses):
    lines = []
    all_ids = set(abs(l) for c in clauses for l in c.lits)
    lines.append("p cnf {0} {1}".format(len(all_ids), len(clauses)))
    for c in clauses:
        line = [str(l) for l in c.lits] + ["0"]
        lines.append(' '.join(line))
    return lines


def initialize(request, remote_repositories, installed_repository, debug=0):
    pool = Pool(remote_repositories)
    pool.add_repository(installed_repository)

    policy = InstalledFirstPolicy(pool, installed_repository)
    solver = DependencySolver(
        pool, remote_repositories, installed_repository,
        policy=policy)

    requirement_ids, rules = solver._create_rules_and_initialize_policy(
        request)
    sat_solver = MiniSATSolver.from_rules(rules, policy)

    return pool, sat_solver, requirement_ids


def to_dimacs(pool, clauses):
    lines = []
    lines.append("c KEY")
    lines.append("c {}".format(json.dumps({
        pkg_id: "{} {}".format(pkg.name, pkg.version)
        for pkg_id, pkg in (
            (pkg_id, pool.id_to_package(pkg_id))
            for pkg_id in pool.package_ids)})))
    lines.extend(clauses_to_dimacs(clauses))
    return lines


def from_dimacs_solution(
        pool, installed_repository, requirement_ids, solution_ids):

    installed_map = set(pool.package_id(p) for p in installed_repository)

    root_ids = installed_map.union(requirement_ids)
    solution_ids = _connected_packages(
        solution_ids, root_ids, pool
    )

    return Transaction(pool, solution_ids, installed_map)


def main(argv=None):
    argv = argv or sys.argv[1:]

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    p.add_argument("--solve", action="store_true",
                   help=("Feed the solution to './minisat' and"
                         " show the resulting solution."))
    p.add_argument("--debug", action="count",
                   help="increase the logging verbosity.")

    ns = p.parse_args(argv)

    fmt = '%(asctime)s %(levelname)-8.8s [%(name)s:%(lineno)s] %(message)s'
    logging.basicConfig(
        format=fmt,
        datefmt='%Y-%m-%d %H:%M:%S',
        level='INFO' if ns.debug else 'WARNING'
    )

    scenario = Scenario.from_yaml(ns.scenario)
    pool, solver, requirement_ids = initialize(
        scenario.request, scenario.remote_repositories,
        scenario.installed_repository,
        debug=ns.debug)

    dimacs = '\n'.join(to_dimacs(pool, solver.clauses))

    if ns.solve:
        PIPE = subprocess.PIPE
        try:
            cmd = ['./minisat', '-strict', '/dev/stdin', '/dev/stdout']
            proc = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except OSError as e:
            msg = str(e) + ": {!r}".format(' '.join(cmd))
            raise OSError(msg)
        output, stderr = proc.communicate(dimacs.encode('ascii'))
        output = output.decode('ascii')
        output = [l.strip() for l in output.splitlines()]
        SAT, model = output[:2]
        if SAT == 'SAT' and model[-2:] == ' 0':
            solution_ids = set(int(i) for i in model.split()[:-1])
            transaction = from_dimacs_solution(
                pool, scenario.installed_repository, requirement_ids,
                solution_ids)
            print(transaction)
    else:
        print(dimacs)

if __name__ == '__main__':
    main()
