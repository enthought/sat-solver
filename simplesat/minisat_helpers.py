import os
import subprocess

DEVNULL = open(os.devnull, 'w')

def rules_set_to_dimacs(pool, rules, fp):
    """
    Translate a rules generator into a dimacs file.

    Parameters
    ----------
    pool: Pool
    rules: RulesGenerator
    fp : file-like object
        A file-like object to write the rules into.
    """
    max_id = pool._id

    fp.write("c written by new_solver\n")
    fp.write("p cnf {0} {1}\n".format(max_id, len(rules)))
    for rule in rules:
        fp.write(" ".join(str(i) for i in rule.literals) + " 0\n")


def solve_sat(pool, rules):
    input_filename = "problem.dimacs"
    output_filename = "problem.sol"

    with open(input_filename, "wt") as fp:
        rules_set_to_dimacs(pool, rules, fp)

    code = subprocess.call(["minisat", input_filename, output_filename],
                           stdout=DEVNULL, stderr=subprocess.STDOUT)
    assert code == 10

    with open(output_filename, "rt") as fp:
        return solution_to_package_strings(fp)


def solution_to_package_strings(fp):
    """
    Convert a minisat solution output file into a set of packages.
    """
    header = fp.readline()
    assert header == "SAT\n"
    data = fp.readline()

    return [int(value) for value in data.split()[:-1]]


def is_satisfable(pool, rules):
    input_filename = "problem.dimacs"
    output_filename = "problem.sol"

    with open(input_filename, "wt") as fp:
        rules_set_to_dimacs(pool, rules, fp)

    code = subprocess.call(["minisat", input_filename, output_filename],
                           stdout=DEVNULL, stderr=subprocess.STDOUT)
    assert code in (10, 20)

    return code == 10
