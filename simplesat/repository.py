from __future__ import absolute_import

import bisect
import collections
import operator

from .errors import NoSuchPackage


class Repository(object):
    """
    A Repository is a set of package, and knows about which package it
    contains.
    """
    def __init__(self, packages=None):
        self._name_to_packages = collections.defaultdict(list)
        # Sorted list of keys in self._name_to_packages
        self._names = []

        packages = packages or []
        for package in packages:
            self.add_package(package)

    def __len__(self):
        return sum(len(self._name_to_packages[p])
                   for p in self._name_to_packages)

    def __iter__(self):
        for name in self._names:
            for package in self._name_to_packages[name]:
                yield package

    def add_package(self, package_metadata):
        if package_metadata.name not in self._name_to_packages:
            bisect.insort(self._names, package_metadata.name)

        self._name_to_packages[package_metadata.name].append(package_metadata)
        # Fixme: this should not be that costly as long as we don't have
        # many versions for a given package.
        self._name_to_packages[package_metadata.name].sort(
            key=operator.attrgetter("version")
        )

    def find_package(self, name, version):
        """Search for the first match of a package with the given name and
        version.

        Parameters
        ----------
        name : str
            The package name to look for.
        version : EnpkgVersion
            The version to look for.

        Returns
        -------
        package : RemotePackageMetadata
            The corresponding metadata.
        """
        candidates = self._name_to_packages[name]
        for candidate in candidates:
            if candidate.version == version:
                return candidate
        raise NoSuchPackage(
            "Package '{0}-{1}' not found".format(name, str(version))
        )

    def find_packages(self, name):
        """ Returns a list of package metadata with the given name,
        sorted from lowest to highest version.

        Parameters
        ----------
        name : str
            The package's name

        Returns
        -------
        packages : iterable
            Iterable of RemotePackageMetadata-like (order is unspecified)
        """
        if name in self._name_to_packages:
            return list(self._name_to_packages[name])
        else:
            return []

    def update(self, repository):
        """ Add the given repository's packages to this repository.
        """
        for package in repository:
            self.add_package(package)
