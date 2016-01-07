import six

from attr import Factory, attr, attributes
from attr.validators import instance_of

from okonomiyaki.versions import EnpkgVersion


@attributes
class RepositoryInfo(object):
    name = attr(validator=instance_of(six.text_type))


@attributes
class PackageMetadata(object):
    name = attr(validator=instance_of(six.text_type))
    version = attr(validator=instance_of(EnpkgVersion))

    dependencies = attr(
        validator=instance_of(tuple),
        default=Factory(tuple),
    )

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


@attributes
class RepositoryPackageMetadata(object):
    repository_info = attr(validator=instance_of(RepositoryInfo))

    _package = attr(validator=instance_of(PackageMetadata))

    @classmethod
    def from_package(cls, package, repository_info):
        return cls(repository_info, package)

    @classmethod
    def _from_pretty_string(cls, s, repository_info):
        package = PackageMetadata._from_pretty_string(s) 
        return cls.from_package(package, repository_info)

    @property
    def name(self):
        return self._package.name

    @property
    def version(self):
        return self._package.version

    @property
    def dependencies(self):
        return self._package.dependencies
