Prototype for SAT-based dependency handling. This is a work in progress,
do not expect any API not to change at this point.

Installation
============

To install the python package, simple do as follows::

    git clone --recursive https://github.com/enthought/sat-solver
    cd sat-solver
    pip install -e .

Example usage
=============

TODO

Usage from the CLI
==================

To try things out from the CLI, you need to write a scenario file (yaml
format), see simplesat/tests/simple_numpy.yaml for a simple example.

To print the rules::

    python scripts/print_rules.py simplesat/tests/simple_numpy.yaml

To print the operations::

    python scripts/solve.py simplesat/tests/simple_numpy.yaml


Comparing with php's composer
=============================

First, clone composer's somewhere on your machine::

    git clone https://github.com/composer/composer

Then, use the `scripts/scenario_to_php.py` script to write a php file that will
print the composer's solution for a given scenario::

    python scripts/scenario_to_php.py \
        --composer-root <path to composer github checkout> \
        simplesat/tests/simple_numpy.yaml \
        scripts/print_operations.php.in

This will create a `scripts/print_operations.php` script you can simply execute w/
php::

    php scripts/print_operations.php

Bibliography
============

- Niklas Eén, Niklas Sörensson: `An Extensible SAT-solver
  <http://minisat.se/downloads/MiniSat.pdf>`_. SAT 2003
- Lintao Zhang, Conor F. Madigan, Matthew H. Moskewicz, Sharad Malik:
  `Efficient Conflict Driven Learning in a Boolean Satisfiability Solver
  <https://www.princeton.edu/~chaff/publication/iccad2001_final.pdf>`_.
  Proc. ICCAD 2001, pp. 279-285.
- Donald Knuth: `The art of computer programming
  <http://www-cs-faculty.stanford.edu/~knuth/fasc6a.ps.gz>`_. Vol. 4,
  Pre-fascicle 6A, Par. 7.2.2.2. (Satisfiability).

On the use of SAT solvers for managing packages:

- Fosdem 2008 presentation: `Using SAT for solving package dependencies
  <https://files.opensuse.org/opensuse/en/b/b9/Fosdem2008-solver.pdf>`_. More
  details on the `SUSE wiki
  <https://en.opensuse.org/openSUSE:Libzypp_satsolver>`_.
- The `0install project <http://0install.net>`_.
- Chris Tucker, David Shuffelton, Ranjit Jhala, Sorin Lerner: `OPIUM: Optimal
  Package Install/Uninstall Manager
  <https://cseweb.ucsd.edu/~lerner/papers/opium.pdf>`_. Proc. ICSE 2007,
  pp. 178-188
