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
cycle recursively though package dependencies, adding new rules as we discover
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
