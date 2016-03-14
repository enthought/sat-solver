Glossary
========

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
      In the object hierarchy, a "package" refers to a ``PackageMetadata``
      instance. This describes a package, its dependencies
      "``install_requires``" and the packages with which it conflicts.

      Colloquially, this refers to any kind of software distribution we might
      be trying to manage.

  Request
      The operations that we wish to apply to the collection of packages. This
      might include installing a new package, removing a package, or upgrading
      all installed packages.

  Requirement
      An object representation of a package range string, such as
      ``numpy > 1.8.2-2`` or ``pip ^= 8.0.1``. These are created from
      dependency information attached to ``PackageMetadata`` and passed to the
      ``Pool`` to query the available packages.
