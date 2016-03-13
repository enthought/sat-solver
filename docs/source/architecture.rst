Architecture
============

Simplesat is modeled after the Composer library from PHP.

Glossary
--------

First, some definitions:

  Repository
      A collection of packages from a single source. An example of repository
      might be the packages already installed on the system, or a set of
      available packages from a package server.

  Pool
      A collection of multiple Repositories. The pool provides an interface
      for querying repositories for packages that satisfy Requirements.

  Policy
      A strategy for proposing the next package to try when the solver must
      make an assumption.

  Package
      In object hierarchy, a "package" refers to a PackageMetadata instance.
      This describes a package, its dependencies "``install_requires``" and the
      packages with which it conflicts.

      Colloquially, this refers to any kind of software distribution we might
      be trying to manage.

  Request
      The operations that we wish to apply to the collection of packages. This
      might include installing a new package, removing a package, or upgrading
      all installed packages.

For a good overview of the public API of the entire system, you should look at
``simplesat.test_utils.Scenario``, upon which all of our functional testing is
based. The ``Scenario`` class shows how to build ``PackageMetadata`` instances
from strings, use them to create a ``Repository``, ``Pool`` and ``Request`` and
pass them to a ``DependencySolver`` for resolution.

Tag said, pictures help. Let's look at how data flows through the object
hierarchy.

Package Hierarchy
-----------------

.. graphviz::

    graph {
        singular;
        plural [shape=tripleoctagon];
    }


A ``RepositoryPackageMetadata`` is the basic object describing a software
package that we might want to install. It has attached to it a collection of
strings describes the packages upon which it depends, referred to as
``installed_requires``, as those with which it ``conflicts``. To avoid paying
the cost of parsing our entire universe of packages for every request, these
attached constraints are not parsed into ``Requirement`` objects until they are
needed. We'll show them like this from now on to make it clear that they don't
exist until needed.

.. graphviz::

    digraph G {
        Requirement [shape=tripleoctagon, style=dashed];
    }


A package object also has a ``RepositoryInfo`` attached to it, which is not
currently used for solving, but provides information about the source of the
package.

.. graphviz::

    digraph G {
        PackageMetadata -> constraint_strings;
        constraint_strings -> Requirement [label = "parses-to", style = dashed];
        PackageMetadata -> RepositoryInfo;
        Requirement [shape=tripleoctagon, style=dashed];
    }

For testing or interactive exploration, these can be created via the
``PrettyPackageStringParser``::

    from okonomiyaki.versions import EnpkgVersion
    ps = PrettyPackageStringParser(EnpkgVersion.from_string)
    package = ps.parse_to_package(
        'foo 1.8.2; install_requires (bar ^= 3.0.0, baz == 1.2.3-4)
        '; conflicts (quux ^= 2.1.2)')

A ``Repository`` is made out of many of these such packages.

.. graphviz::

    digraph G {
        Repository -> PackageMetadata
        PackageMetadata -> RepositoryInfo;
        PackageMetadata -> Requirement;
        Requirement [shape=tripleoctagon, style=dashed];
        PackageMetadata [shape=tripleoctagon];
    }

and can be created from them like so::

    repo = Repository(iter_of_packages)
    repo.add_package(additional_package)

The ``Repository`` class is rather simple and does not support any kind of
complicated querying. When it is time to identify packages according to
constraints such as ``"numpy >= 1.7.2"``, we must create a ``Pool``. A ``Pool``
can contain many such ``Repository`` and expose an API for querying.

.. graphviz::

    digraph G {
        Pool -> Repository
        Repository -> PackageMetadata
        PackageMetadata -> RepositoryInfo;
        PackageMetadata -> Requirement;
        Requirement [shape=tripleoctagon, style=dashed];
        Repository [shape=tripleoctagon];
        PackageMetadata [shape=tripleoctagon];
    }

The ``Pool`` is used like so::

    repository = Repository(packages)
    requirement = Requirement._from_string("numpy ^= 1.8.1")
    pool = Pool([repository])
    package_metadata_instances = pool.what_provides(requirement)


Requests
--------

.. graphviz::

    digraph simplesat {
        DependencySolver -> Policy;
        DependencySolver -> Pool;
        DependencySolver -> MiniSat [constraint = false];
        MiniSat -> Policy;
        Policy -> Pool [constraint = false];
        Pool -> Request;
        Request -> Job;
        Request -> Job;
        Job -> Requirement;
        Request -> ConstraintModifiers;
        Pool -> Repository;
        Pool -> Repository;
        Repository -> PackageMetadata;
        Repository -> PackageMetadata;
        PackageMetadata -> Requirement;
        PackageMetadata -> Requirement;

        Repository [shape=tripleoctagon];
        Job [shape=tripleoctagon];
        Requirement [shape=tripleoctagon];
        PackageMetadata [shape=tripleoctagon];
    }
