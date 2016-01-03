=======================
``simplesat`` CHANGELOG
=======================

Changes since version 0.1.0
===========================

Enhancements
------------

* Details relating to unsatisfiable scenarios are captured in an ``UNSAT``
  object and attached to the ``SatisifiabilityError`` raised (#101).

Bugs Fixed
----------

* ``IPolicy`` constructor now ignores initialization arguments (#101).
* Some sort operations that were using non-unique keys have been fixed (#101).
* Assumptions are now represented as an empty Clause object (#101).

Changes since version 0.1.0
===========================

Version 0.1.0
=============

The initial release of ``simplesat``. While the SAT solver is fully functional,
the infrastructure for building a set of clauses to be solved supports runtime
dependencies specified using only equality constraints, such as ``numpy 1.8.0-1
depends MKL ~= 10.3``.

Features
--------

* Provides a pure python implementation of MiniSAT, supporting directed search
  via plugin-style ``Policy`` objects.
* Reads and solves yaml-based scenario descriptions. These may optionally
  specify the following:

  * available packages
  * currently installed packages
  * "marked" packages which must be present in a valid solution
  * any number of requested package-oriented operations

    * installation
    * removal
    * update
    * update-all

  * the expected solution as a list of such package operations
  * a failure message for scenarios which are expected to be unresolvable.

* Keeps detailed information about the progression of value assignments and
  assumptions made throughout the search process.
* Make some effort to prune irrelevant truth values from solutions, i.e. find
  the minimal set of values needed to solve a problem.
>>>>>>> fb1d985... MAINT: update changelog
