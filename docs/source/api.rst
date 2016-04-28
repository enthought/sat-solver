.. _api:

API Reference
=============

This covers all of the interfaces in Simplesat. For an overview of how these
pieces fit together, take a look at :ref:`architecture`.

Main Interface
--------------

For testing of the validity of a set of requirements, typical usage might be
the following::

    installed_repository = Repository([package1, package2])
    remote_repository = Repository([package1, package3, package4])

    R = Requirment.from_string
    requirements = [R('package1 > 1.2.3'), R('package4 < 2.8')]
    repositories = [installed_repository, remote_repository]

    if packages_are_consistent(installed_repository):
        print("Installed packages are OK!")

    if requirements_are_satisfiable(repositories, requirements):
        print("The requirements are mutually compatible.")
    else:
        print("The requirements conflict.")

    if requirements_are_complete(repositories, requirements):
        print("These requirements include all necessary dependencies.")
    else:
        print("The requirements are incomplete. Dependencies are missing.")

.. autofunction:: simplesat.dependency_solver.packages_are_consistent
.. autofunction:: simplesat.dependency_solver.requirements_are_complete
.. autofunction:: simplesat.dependency_solver.requirements_are_satisfiable
.. autofunction:: simplesat.dependency_solver.satisfy_requirements
.. autofunction:: simplesat.dependency_solver.simplify_requirements
.. automodule:: simplesat.constraints.requirement
    :members:

Functional classes
------------------
Internally, these make use of the :class:`DependencySolver`. To use it
yourself, you'll need to create some :class:`Packages <PackageMetadata>`,
populate at least one :class:`Repository` with them, add *that* to a
:class:`Pool` and give all of that to the constructor. Then you can make some
:class:`Requirements<Requirement>` that describe what you'd like to do, add
them to a :class:`Request` and pass it to
:meth:`solve<DependencySolver.solve>`.

.. autoclass:: simplesat.dependency_solver.DependencySolver
    :members:

.. automodule:: simplesat.request
    :members:

.. automodule:: simplesat.sat.policy

Package Hierarchy
-----------------

.. automodule:: simplesat.package
    :members:

.. automodule:: simplesat.repository
    :members:

.. automodule:: simplesat.pool
    :members:

Conveniences
------------

.. automodule:: simplesat.constraints.package_parser
    :members:

.. automodule:: simplesat.test_utils
    :members:

.. autofunction:: simplesat.dependency_solver.requirements_from_packages
.. autofunction:: simplesat.dependency_solver.packages_from_requirements

Exceptions
----------
.. automodule:: simplesat.errors
    :members:

Lower level utilities
---------------------
These are used internally.

.. automodule:: simplesat.utils.graph
    :members:
