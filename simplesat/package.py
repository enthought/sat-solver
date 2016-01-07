import six

from attr import attr, attributes
from attr.validators import instance_of

from okonomiyaki.versions import EnpkgVersion


@attributes
class RepositoryInfo(object):
    name = attr(validator=instance_of(six.text_type))


@attributes
class PackageMetadata(object):
    name = attr(validator=instance_of(six.text_type))
    version = attr(validator=instance_of(EnpkgVersion))

    dependencies = attr(validator=instance_of(tuple))

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
class RepositoryPackageMetadata(PackageMetadata):
    repository_info = attr(validator=instance_of(RepositoryInfo))

    @classmethod
    def from_package(cls, package, repository_info):
        return cls(
            package.name, package.version, package.dependencies,
            repository_info
        )

    @classmethod
    def _from_pretty_string(cls, s, repository_info):
        package = PackageMetadata._from_pretty_string(s) 
        return cls.from_package(package, repository_info)
