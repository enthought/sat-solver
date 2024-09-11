``simplesat`` CHANGELOG
=======================

Version 0.9.1
-------------

* Fix the simplesat wheel build (#287)

Version 0.9.0
-------------

* Replace travis CI with Github Actions (#281)
* Run tests for Python 3.11 (#284)

Version 0.8.2
-------------

Released on October 8th, 2019.

* Fix deprecated ``convert`` attribute in ``constraint_modifiers.py`` to
  comply with attrs package release 19.2.0 (see also
  `<https://www.attrs.org/en/stable/changelog.html>`_). (#270)
* Fix typo in ``InvalidConstraint`` error message. (#266)
* Fix error with ``UndeterminedClausePolicy`` not suggesting best packages. (#268)

Internals
~~~~~~~~~

* Change minimum supported version of attrs to 17.4.0. (#270)


Version 0.8.1
-------------

Released on March 22nd, 2017.

Bug fixes
~~~~~~~~~

* fix edge case in upgrade-all, when no remote candidate is available for an
  already installed package (#261)
* fix parsing of requirements that start with a digit (#260)

Version 0.8.0
-------------

Released on March 9th, 2017.

Features
~~~~~~~~

* new upgrade job kind, to update every installed package to the latest (#253)
* new solver method solve_with_hint for a more human-readable message for
  unsatisfiable problems (#254)

Internals
~~~~~~~~~

* update runtime dependencies constraints to latest okonomiyaki (#252)


Version 0.7.0
-------------

Released on August 8th, 2016.

Features
~~~~~~~~

* Add function to compute the leaf packages in a set of repositories.

Version 0.6.0
-------------

Released on July 20th, 2016.

Features
~~~~~~~~

* Add support for post-release version number (#239)
* Add package and package id iteration to Pool (#237)

Version 0.5.0
-------------

Released on July 12th, 2016.

Features
~~~~~~~~~

* Return error message text when checking for satisfiability/completeness of
  requirements (#231)
* Add `remove` method to ConstraintModifiers that deletes constraints
  associated with a particular package (#229)

Version 0.4.0
-------------

Released on 1st June 2016.

Features
~~~~~~~~~

* `ConstraintModifiers` enhancements: Add `update` method; use validator for
  modifiers on `Request` (#211)
* Add function to compute some minimal unsatisfiable subsets of a set of
  clauses (#219)
* Add `soft-update` job to `Request`. For a soft-update, the policy prefers to
  suggest newer versions rather than the installed version. (#220)

Bug fixes
~~~~~~~~~

* Track clauses with only one literal in solver to avoid crash in policy (#209)
* Avoid failure in policy if an installed package has no associated clauses
  (#218)

Version 0.3.0
-------------

Released on 5th May 2016.

Features
~~~~~~~~~

* add support for `provides` metadata (#194)
* add new api for simplifying and satisfying requests (#195)

Enhancements
------------

* update `install_requires` to allow `okonomiyaki >= 0.14` (#197)
* Request now uses `attrs` (#196)
* update internal documentation for the various Requirement types (#201)

Bug fixes
~~~~~~~~~

* fix `Repository.add_package` when `Repository.find_packages` was previously
  used for non existing packages (#185)
* fix error handling when metadata conflict (#187)
* fix package name parsing in requirement (#193)
* call to `asdict` must be deterministic (#200)

Version 0.2.2
-------------

Released on 29/04/2016.

* update `install_requires` to allow `okonomiyaki >= 0.14` (#198)

Version 0.2.1
-------------

Released on 27/04/2016.

* fix `Repository.add_package` when `Repository.find_packages` was previously
  used for non existing packages (#185)
* fix error handling when metadata conflict (#187)

Version 0.2.0
-------------

Enhancements
~~~~~~~~~~~~

* Details relating to unsatisfiable scenarios are captured in an ``UNSAT``
  object and attached to the ``SatisifiabilityError`` raised (#101).
* satsolver does not depend on enstaller anymore, and only uses non-Enthought
  libraries besides okonomiyaki (#127, #114, #113, #111, #110, #109, #107.
  #105)
* support ad-hoc relaxing of dependency requirements (#140)
* added documentation
* handle the case where a package metadata contains reference to non existing
  requirements. Those are now by default ignored instead of just crashing the
  solver (#156)
* added __version__ and __git_revision__ attributes to satsolver (#173)

Bugs Fixed
~~~~~~~~~~

* ``IPolicy`` constructor now ignores initialization arguments (#101).
* Some sort operations that were using non-unique keys have been fixed (#101).
* Assumptions are now represented as an empty Clause object (#101).
* be stricted about distribution name and version parsing (#146)
* cleanup setup, added missing enum34 as a dependency in setup.py (#169, #170)

Internals
~~~~~~~~~

* internal API to check consistency of a set of requirements (#157)
* fix debug output in scripts/solve.py (#159)
* add utility script to export a scenario into DIMACS format (#162)
* internal API to compute reverse dependencies of a requirement (#175)

Version 0.1.0
~~~~~~~~~~~~~

The initial release of ``simplesat``. While the SAT solver is fully functional,
the infrastructure for building a set of clauses to be solved supports runtime
dependencies specified using only equality constraints, such as ``numpy 1.8.0-1
depends MKL ^= 10.3``.

Features
~~~~~~~~

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
