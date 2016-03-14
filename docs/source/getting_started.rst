Getting Started
===============

Installation
------------

To install the python package, do as follows::

    git clone --recursive https://github.com/enthought/sat-solver
    cd sat-solver
    pip install -e .

Usage from the CLI
------------------

To try things out from the CLI, you need to write a scenario file (YAML
format), see ``simplesat/tests/simple_numpy.yaml`` for a simple example.

To print the rules::

    python scripts/print_rules.py simplesat/tests/simple_numpy.yaml

To print the operations::

    python scripts/solve.py simplesat/tests/simple_numpy.yaml
