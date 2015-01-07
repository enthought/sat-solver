import subprocess


def rules_set_to_dimacs(rules_generator, fp):
    """
    Translate a rules generator into a dimacs file.

    Parameters
    ----------
    rules_generator : RulesGenerator
    fp : file-like object
        A file-like object to write the rules into.
    """
    pool = rules_generator._pool
    max_id = pool._id

    rules_set = rules_generator.iter_rules()
    fp.write("c written by new_solver\n")
    fp.write("p cnf {0} {1}\n".format(max_id, len(rules_set)))
    for rule in rules_set:
        fp.write(" ".join(str(i) for i in rule.literals) + " 0\n")


def solve_sat(pool, rules_generator):
    input_filename = "problem.dimacs"
    output_filename = "problem.sol"

    with open(input_filename, "wt") as fp:
        rules_set_to_dimacs(rules_generator, fp)

    code = subprocess.call(["minisat", input_filename, output_filename])
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
