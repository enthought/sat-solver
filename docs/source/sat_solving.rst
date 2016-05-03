SAT Solving
===========

Encoding Relationships as Clauses
---------------------------------

The ``RulesGenerator`` is responsible for rooting out all
of the relevant packages for this problem and creating ``PackageRule`` objects
describing their relationships. An example might be translating a requirement
such as ``numpy`` into ``(+numpy-1.8.1 | +numpy-1.8.2 | +numpy-1.8.3)``,
where the ``+`` operator indicates that the package should be installed and
``|`` is logical OR. In prose one might read this as "Must install one of
``numpy-1.8.1``, ``numpy-1.8.2``, or ``numpy-1.8.3``."

To build up a total set of rules, we start at each of our ``Job`` rules and
cycle recursively though package metadata, adding new rules as we discover
new packages. This is done by running each of our requirements through the
``Pool`` and asking it which packages match.


Constraint Modifiers
--------------------

The key notion here is that ``Pool.what_provides()`` gives us a very flexible
abstraction for package querying. When we want to manipulate the way package
dependencies are handled, we don't need to modify the packages themselves, it
is enough to modify the querying function such that it *responds* in the way
that we want.

We attach the ``ConstraintModifiers`` to the ``Pool`` itself, and at query
time, the ``Pool`` may *transform* the ``Requirement`` as necessary. The
current implementation results in the transformations below. The original
requirement is on the far left, with the result of each type of transformation
to the right of it. ``*`` is a wild-card that matches any version.

===============  ===============   ===============  ===============
 Original          Allow newer       Allow older      Allow any
===============  ===============   ===============  ===============
``*``             ``*``            ``*``            ``*``
``> 1.1.1-1``     ``> 1.1.1-1``    ``*``            ``*``
``>= 1.1.1-1``    ``>= 1.1.1-1``   ``*``            ``*``
``< 1.1.1-1``     ``*``            ``< 1.1.1-1``    ``*``
``<= 1.1.1-1``    ``*``            ``<= 1.1.1-1``   ``*``
``^= 1.1.1``      ``>= 1.1.1``     ``<= 1.1.1-*``   ``*``
``== 1.1.1-1``    ``>= 1.1.1-1``   ``<= 1.1.1-1``   ``*``
``!= 1.1.1-1``    ``!= 1.1.1-1``   ``!= 1.1.1-1``   ``!= 1.1.1-1``
===============  ===============   ===============  ===============


Requirements
------------

There are currently three different ``Requirement`` classes:
:class:`Requirement<simplesat.constraints.requirement.Requirement>`,
:class:`InstallRequirement
<simplesat.constraints.requirement.InstallRequirement>` and
:class:`ConflictRequirement
<simplesat.constraints.requirement.ConflictRequirement>`. They have no internal
differences, but this split allows us to reliably track the origin of a
requirement via its type and avoid using it in an inappropriate context.

We care about the difference between a requirement created from
``package.install_requires`` vs one created from ``package.conflicts`` vs one
created from parsing a pretty string into a Job. It only makes sense for
``modifiers`` to apply to constraints created from ``install_requires``; we
don't want to modify a constraint that the user explicitly gave us and we don't
know what it means to ``allow_newer`` for a conflicts constraint at all.
By creating an ``InstallRequirement`` only when reading
``package.install_requires`` and then explicitly checking for that class at the
only point where we might modify it, we can prevent ourselves from modifying
the wrong kind of requirement. The same goes for ``ConflictRequirement``,
although there is currently no use case differentiating it from a plain
``Requirement``.

Top-level ("Job") requirements are created by external code because the only
way to communicate a requirement to the system is via a ``Requirement`` object
attached to a ``Request``. All others are created as needed by the
``RulesGenerator`` while it puts together rules based on package metadata.

So user-given requirements like ``install foo^=1.0`` or ``update bar`` are
turned into normal ``Requirement`` objects because they should *not* be
modified. **Getting this wrong can lead to "install inconsistent sets of
packages" bugs.**

When to use each requirement class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`InstallRequirement <simplesat.constraints.requirement.InstallRequirement>`
  Requirements derived from ``package.install_requires`` metadata. For
  example::

      for constraints in package.install_requires:
        req = InstallRequirement.from_constraints(constraints)

  .. note::
    Currently, this is the only type of requirement that can be passed to
    ``modify_requirement``.

:class:`ConflictRequirement <simplesat.constraints.requirement.ConflictRequirement>`
  Requirements derived from ``package.conflicts`` metadata. For example::

      for constraints in package.conflicts:
        req = ConflictRequirement.from_constraints(constraints)

:class:`Requirement<simplesat.constraints.requirement.Requirement>`,
  All other requirements, including those coming directly from a user via a
  :class:`simplesat.request.Request`.
