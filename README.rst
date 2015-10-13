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

    python scripts/solve.py simplesat/tests/simple_numpy.yaml

What is known to work:

* runtime dependency handling from a virgin state, either using the most
  recent requirement or an older one. See the iris.yaml for a non trivial
  example.

Known not to work:

* the installed first policy implementation is really slow when many
  packages are already installed
* remove/upgrade: not handled yet
* update: slow and solution often subobtimal.

Bibliography:

- Niklas Een, Niklas Sorensson: `An Extensible SAT-solver
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
  

  
