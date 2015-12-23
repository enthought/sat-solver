=====================
`simplesat` CHANGELOG
=====================

Version 0.1.0
=============

The initial release of `simplesat`.

Features
--------

* Provides a pure python implementation of MiniSAT, supporting directed search
  via plugin-style `Policy` objects.
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
