import abc
import six

from okonomiyaki.versions import EnpkgVersion


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
    @classmethod
    def _from_pretty_string(cls, s):
        """ Create an instance from a pretty string.

        A pretty string looks as follows::

            'numpy 1.8.1-1; depends (MKL ~= 10.3)'

        Note
        ----
        Don't use this in production code, only meant to be used for testing.
        """
        # FIXME: local import to workaround circular imports
        from .constraints import PrettyPackageStringParser
        parser = PrettyPackageStringParser(EnpkgVersion.from_string)
        return parser.parse_to_package(s)

    def __init__(self, name, version, dependencies=None):
        self._name = name
        self._version = version
        self._dependencies = dependencies or tuple()

        self._key = (name, version, self._dependencies)
        self._hash = hash(self._key)

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def dependencies(self):
        return self._dependencies

    def __repr__(self):
        return "PackageMetadata('{0}-{1}')".format(self._name, self._version)

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

    @property
    def name(self):
        return self._package.name

    @property
    def version(self):
        return self._package.version

    @property
    def dependencies(self):
        return self._package.dependencies

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
