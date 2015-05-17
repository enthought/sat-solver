Prototype for SAT-based dependency handling. This is a work in progress,
do not expect any API not to change at this point.

To set things up, inside a virtualenv::

    git clone --recursive https://github.com/enthought/sat-solver
    cd sat-solver
    (cd dependencies/enstaller && python setup.py develop)
    python setup.py develop

To try things out, you need to write a scenario file (yaml format), see
simplesat/tests/simple_numpy.yaml for a simple example.

To print the rules::

    python scripts/print_rules.py simplesat/tests/simple_numpy.yaml

To print the operations::

    python scripts/pysolver_policy.py simplesat/tests/simple_numpy.yaml

What is known to work:

* runtime dependency handling from a virgin state, either using the most
  recent requirement or an older one. See the iris.yaml for a non trivial
  example.

Known not to work:

* the installed first policy implementation is really slow when many
  packages are already installed
* remove/upgrade: not handled yet
* update: slow and solution often subobtimal.
