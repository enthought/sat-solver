.. _architecture:

Architecture
============

Simplesat's API is modeled after the Composer library from PHP.

For a good overview of the public API of the entire system, you should look at
the :class:`Scenario <simplesat.test_utils.Scenario>`, upon which all of our
functional testing is based. The Scenario class shows how to build
:class:`PackageMetadata <simplesat.package.PackageMetadata>` instances from
strings, use them to create a :class:`Repository
<simplesat.repository.Repository>`, :class:`Pool <simplesat.pool.Pool>` and
:class:`Request <simplesat.request.Request>` and pass them to a
:class:`DependencySolver <simplesat.dependency_solver.DependencySolver>` for
resolution.

That said, pictures help. Let's look at how data flows through the object
hierarchy. We'll use the following symbols to indicate singular objects and
plural collections of objects.

.. graphviz::

    graph {
        singular;
        plural [shape=tripleoctagon];
    }


Requests
--------

The purpose of the ``simplesat`` library as a whole is to produce a valid
assignment of package states (installed or not) that satisfy some particular
set of constraints. This is expressed as a
:class:`Transaction<simplesat.transaction.Transaction>` that is to be applied
to the "installed" repository. The :class:`Request <simplesat.request.Request>`
object is our vehicle for communicating these constraints to the solver.


At its core, a :class:`Request <simplesat.request.Request>` is a collection of
actions such as "install" and
:class:`Requirement<simplesat.requirement.Requirement>` objects describing
ranges, such as ``numpy >= 1.8.1``, which together form ``Job`` rules. The
:class:`Request <simplesat.request.Request>` can have any number of such jobs,
all of which must be satisfiable simultaneously. If conflicting jobs are given,
then the solver will fail with a :exc:`simplesat.errors.SatisifiabilityError`.

.. graphviz::

    digraph simplesat {
        Request -> Job;
        Job [shape=tripleoctagon];
    }


Constraint Modifiers
~~~~~~~~~~~~~~~~~~~~

Additionally, one may attach
:class:`ConstraintModifiers<simplesat.constraints.ConstraintModifiers>` to the
:class:`Request <simplesat.request.Request>`. These
are used to modify the constraints of packages during the search for a
solution.

.. graphviz::

    digraph simplesat {
        Request -> Job;
        Request -> ConstraintModifiers;
        Job [shape=tripleoctagon];
    }

These constraints are not applied to the jobs themselves, only to their
dependencies. For example, if one were to create an install job for ``pandas <
0.17``, while at the same time specifying a constraint modifier that allows
any version of pandas to satisfy any constraint, the modifier should *not* be
applied. We assume that any constraint directly associated with a ``Job`` is
explicit and intentional.

Note that :class:`Request <simplesat.request.Request>` objects do not carry any
direct information about packages. They merely describes constraints that any
solution of packages states must satisfy.

Package Hierarchy
-----------------

A :class:`RepositoryPackageMetadata
<simplesat.package.RepositoryPackageMetadata>` is the basic object describing a
software package that we might want to install. It has attached to it a
collection of strings describing the packages upon which it depends, referred
to as ``installed_requires``, as those with which it ``conflicts``. To avoid
paying the cost of parsing our entire universe of packages for every request,
these attached constraints are not parsed into
:class:`Requirement<simplesat.requirement.Requirement>` objects until they are
passed to the :class:`Pool<simplesat.pool.Pool>` later on. We'll show them like
this from now on to make it clear that they don't exist until needed.

.. graphviz::

    digraph G {
        Requirement [shape=tripleoctagon, style=dashed];
    }


RepositoryInfo
~~~~~~~~~~~~~~

A package object also has a
:class:`RepositoryInfo<simplesat.package.RepositoryInfo>` attached to it,
which is not currently used for solving, but provides information about the
source of the package.

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

Repository
~~~~~~~~~~

A ``Repository`` is made out of many of these such packages.

.. graphviz::

    digraph G {
        Repository -> PackageMetadata;
        PackageMetadata -> RepositoryInfo;
        PackageMetadata -> Requirement;
        Requirement [shape=tripleoctagon, style=dashed];
        PackageMetadata [shape=tripleoctagon];
    }

and can be created from them like so::

    repo = Repository(iter_of_packages)
    repo.add_package(additional_package)


Pool
~~~~

The ``Repository`` class does not support any kind of complicated querying.
When it is time to identify packages according to constraints such as ``numpy
>= 1.7.2``, we must create a :class:`Pool<simplesat.pool.Pool>`. A
:class:`Pool<simplesat.pool.Pool>` contains many such ``Repository`` objects
and exposes an API to query them for packages.

.. graphviz::

    digraph G {
        Pool -> Repository;
        Pool -> ConstraintModifiers;
        Repository -> PackageMetadata;
        PackageMetadata -> RepositoryInfo;
        PackageMetadata -> Requirement;
        Requirement [shape=tripleoctagon, style=dashed];
        Repository [shape=tripleoctagon];
        PackageMetadata [shape=tripleoctagon];
    }

The :class:`ConstraintModifiers<simplesat.constraints.ConstraintModifiers`
object is also attached to the :class:`Pool<simplesat.pool.Pool>`. It is used
to modify incoming :class:`Requirement<simplesat.requirement.Requirement>`
objects before using them to query for matching packages. This happens
implicitly in the
:meth:`Pool.what_provides()<simplesat.pool.Pool.what_provides>` method. The
result of such modification can be inspected directly by calling
:meth:`Pool.modify_requirement()<simplesat.pool.Pool.modify_requirement>`,
which is used internally. The :class:`Pool<simplesat.pool.Pool>` is used like
so::

    repository = Repository(packages)
    requirement = InstallRequirement._from_string("numpy ^= 1.8.1")
    pool = Pool([repository], modifiers=ConstraintModifiers())
    package_metadata_instances = pool.what_provides(requirement)

    # These are not modified. Used for handling e.g. jobs.
    more_instances = pool.what_provides(requirement, modify=False)

We now have a complete picture describing the organization of package data.

.. graphviz::

    digraph simplesat {
        Request -> Job;
        Job -> Requirement;
        Request -> ConstraintModifiers;
        Pool -> Repository;
        Repository -> PackageMetadata;
        Pool -> ConstraintModifiers [constraint = false];
        PackageMetadata -> Requirement;

        Repository [shape=tripleoctagon];
        Job [shape=tripleoctagon];
        Requirement [shape=tripleoctagon];
        PackageMetadata [shape=tripleoctagon];
    }

MiniSAT Engine
--------------

When it comes time to process a :class:`Request <simplesat.request.Request>`
and find a suitable set of package assignments, we must create a
``DependencySolver``. This in turn will initialize four pieces that together
work to resolve the request.

- The first is the :class:`Pool<simplesat.pool.Pool>`, which we've already seen.
- The :class:`Pool<simplesat.pool.Pool>` is passed along with the :class:`Request
  <simplesat.request.Request>` to a ``RulesGenerator``,
  which generates an appropriate set of conjunctive normal form (CNF) clauses
  describing the problem.
- Next is the ``Policy``, which determines the order in which new package
  assignments are tried. The simplest possible ``Policy`` could suggest
  unassigned packages in arbitrary order, but typically we will want to do
  something more sophisticated.
- Lastly, we create a ``MiniSat`` object and feed it the rules from the
  ``RulesGenerator`` and the ``Policy`` to help make suggestions when it gets
  stuck. This is the core SAT solving engine. It is responsible for exploring
  the search space and returning an ``AssignmentSet`` that satisfies the
  clauses.

.. graphviz::

    digraph simplesat {
        DependencySolver -> Policy;
        DependencySolver -> Pool;
        DependencySolver -> RulesGenerator [style = dashed];
        RulesGenerator -> Pool [constraint = false];
        DependencySolver -> MiniSat [constraint = false];
        MiniSat -> AssignmentSet;
        MiniSat -> Policy;
        Policy -> AssignmentSet [style = dashed, constraint = false];
        Policy -> Pool;

        RulesGenerator [style = dashed];
    }

As the ``MiniSat`` explores the search space, it will update the
``AssignmentSet``. When it reaches a point where it must make a guess to
continue it will ask the ``Policy`` for a new package to try. The ``Policy``
looks at the ``AssignmentSet`` and :class:`Pool<simplesat.pool.Pool>` to choose
a suitable candidate. This continues until either the ``MiniSat`` finds a
solution or determines that the problem is unsatisifiable.

The entire system looks like this.

.. graphviz::

    digraph simplesat {
        DependencySolver -> Policy;
        DependencySolver -> Pool;
        DependencySolver -> Request;
        DependencySolver -> MiniSat [constraint = false];
        DependencySolver -> RulesGenerator [style = dashed];
        RulesGenerator -> Pool [constraint = false];
        MiniSat -> Policy;
        MiniSat -> AssignmentSet;
        Policy -> AssignmentSet [constraint = false];
        Policy -> Pool;
        Pool -> Repository;
        Repository -> PackageMetadata;
        PackageMetadata -> Requirement;
        Pool -> ConstraintModifiers [constraint = false];
        Job -> Requirement;
        Request -> ConstraintModifiers;
        Request -> Job;

        Repository [shape=tripleoctagon];
        Job [shape=tripleoctagon];
        Requirement [shape=tripleoctagon];
        PackageMetadata [shape=tripleoctagon];
        RulesGenerator [style = dashed];
    }
