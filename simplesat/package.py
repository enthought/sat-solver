import abc
import six
import enum

from okonomiyaki.versions import EnpkgVersion
from simplesat.constraints.requirement import Requirement
from simplesat.constraints.requirement_transformation import (
    transform_install_requires, transform_conflicts
)


class ConstraintKinds(enum.Enum):
    install_requires = 'install_requires'
    conflicts = 'conflicts'


class IRepositoryInfo(six.with_metaclass(abc.ABCMeta)):
    @abc.abstractproperty
    def name(self):
        """ A name that uniquely indentifies a repository."""


class RepositoryInfo(IRepositoryInfo):
    def __init__(self, name):
        self._name = name
        self._key = (name,)
        self._hash = hash(self._key)

    @property
    def name(self):
        return self._name

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._key == other._key

    def __ne__(self, other):
        return self._key != other._key

    def __repr__(self):
        return "Repository(<{0.name}>)".format(self)


class PackageMetadata(object):
    """ PackageMetadata represents an immutable, versioned Python distribution
    and its relationship with other packages.
    """

    @classmethod
    def _from_pretty_string(cls, s):
        """ Create an instance from a pretty string.

        A pretty string looks as follows::

            'numpy 1.8.1-1; depends (MKL ^= 10.3)'

        Note
        ----
        Don't use this in production code, only meant to be used for testing.
        """
        # FIXME: local import to workaround circular imports
        from .constraints import PrettyPackageStringParser
        parser = PrettyPackageStringParser(EnpkgVersion.from_string)
        return parser.parse_to_package(s)

    def __init__(self, name, version, install_requires=None, conflicts=None,
                 parent_package=None):
        """ Return a new PackageMetdata object.

        Parameters
        ----------
        name : str
            The name of the Python distribution, e.g. "numpy"
        version : EnpkgVersion
            An EnpkgVersion object describing the version of this package.
        install_requires : tuple(tuple(str, tuple(tuple(str))))
            A tuple of tuples mapping distribution names to disjunctions of
            conjunctions of version constraints.

            For example, a consider a package that depends on the following:
                - nose
                - six (> 1.2, <= 1.2.3), or >= 1.2.5-2
                    Written as intervals, (1.2, 1.2.3] or [1.2.5-2, \infty)
                - MKL >= 10.1, < 11

            The constraint tuple representing this would be:
                (("MKL", ((">= 10.1", "< 11"),)),
                 ("nose", (("*",),)),
                 ("six", (("> 1.2", "<= 1.2.3"), (">= 1.2.5-2",)))

        conflicts : tuple(tuple(str, tuple(tuple(str))))
            A tuple of tuples mapping distribution names to disjunctions of
            conjunctions of version constraints.

            This works the same way as install_requires, but instead denotes
            packages that must *not* be installed with this package.
        """
        self._name = name
        self._version = version
        self._install_requires = install_requires or ()
        self._conflicts = conflicts or ()
        self._key = (name, version, self._install_requires, self._conflicts)
        self._hash = hash(self._key)

        # Keep track of whether this package was derived from another one
        self.parent_package = parent_package

    def clone_with_modifiers(self, modifiers):
        if modifiers is None:
            return self

        targets = modifiers.targets
        modified = False
        new_install_requires = []
        for name, disjunction in self.install_requires:
            if name in targets:
                modified = True
                requirement = transform_install_requires.with_modifiers(
                    Requirement.from_constraints((name, disjunction)),
                    modifiers)
                new_install_requires.append(requirement.to_constraints())
            else:
                new_install_requires.append((name, disjunction))
        new_install_requires = tuple(new_install_requires)

        new_conflicts = []
        for name, disjunction in self.conflicts:
            if name in targets:
                modified = True
                requirement = transform_conflicts.with_modfiers(
                    Requirement.from_constraints((name, disjunction)),
                    modifiers)
                new_conflicts.append(requirement.to_constraints())
            else:
                new_conflicts.append((name, disjunction))
        new_conflicts = tuple(new_conflicts)

        return self if not modified else type(self)(
            self._name, self._version,
            install_requires=new_install_requires,
            conflicts=new_conflicts,
            parent_package=self
        )

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def install_requires(self):
        return self._install_requires

    @property
    def conflicts(self):
        return self._conflicts

    def __repr__(self):
        return "{0}('{1}-{2}')".format(
            self.__class__.__name__, self._name, self._version)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._key == other._key

    def __ne__(self, other):
        return self._key != other._key


class RepositoryPackageMetadata(object):
    @classmethod
    def _from_pretty_string(cls, s, repository_info):
        package = PackageMetadata._from_pretty_string(s)
        return cls(package, repository_info)

    def __init__(self, package, repository_info):
        self._package = package
        self._repository_info = repository_info

        self._key = (package._key, repository_info)
        self._hash = hash(self._key)

    def clone_with_modifiers(self, modifiers):
        if modifiers is None:
            return self
        new_package = self._package.clone_with_modifiers(modifiers)
        return self if new_package is self._package else type(self)(
            new_package, self._repository_info)

    @property
    def name(self):
        return self._package.name

    @property
    def version(self):
        return self._package.version

    @property
    def install_requires(self):
        return self._package.install_requires

    @property
    def conflicts(self):
        return self._package.conflicts

    @property
    def parent_package(self):
        return self._package.parent_package

    @property
    def repository_info(self):
        return self._repository_info

    def __repr__(self):
        return (
            "RepositoryPackageMetadata('{pkg._name}-{pkg._version}'"
            ", repo={repository_info!r})".format(
                pkg=self._package, repository_info=self._repository_info))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._key == other._key

    def __ne__(self, other):
        return self._key != other._key
