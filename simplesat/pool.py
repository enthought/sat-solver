from __future__ import absolute_import

import itertools
from functools import wraps

from .utils import DefaultOrderedDict


def no_dirty(method):
    @wraps(method)
    def inner(pool, *a, **kw):
        if pool._dirty:
            pool._prepare_packages()
            pool._dirty = False
        return method(pool, *a, **kw)
    return inner


class Pool(object):
    """ A pool of repositories.

    The main feature of a pool is to search for every package matching a
    given requirement.
    """

    def __init__(self, repositories=None, modifiers=None):
        self._repositories = []
        self._modifiers = None
        self.modifiers = modifiers
        self._reset_packages()

        for repository in repositories or []:
            self.add_repository(repository)

    def _reset_packages(self):
        # When true, we must transform the packages we have according to the
        # modifiers before we can use them
        self._dirty = True
        self._original_packages = []
        # FIXME Mar-9-2016: temporarily changing these names to catch places
        # that were using the private API. If it has been awhile and you feel
        # like everything is ok, you can remove these trailing underscores.
        self._package_to_id_ = {}
        self._id_to_package_ = {}
        self._packages_by_name_ = DefaultOrderedDict(list)

    @property
    def modifiers(self):
        return self._modifiers

    @modifiers.setter
    def modifiers(self, value):
        self._dirty = True
        self._modifiers = value

    def add_repository(self, repository):
        """ Add the repository to this pool.

        Parameters
        ----------
        repository : Repository
            The repository to add
        """
        self._dirty = True
        self._repositories.append(repository)
        self._original_packages.extend(repository)

    @no_dirty
    def what_provides(self, requirement):
        """ Computes the list of packages fulfilling the given
        requirement.

        Parameters
        ----------
        requirement : Requirement
            The requirement to match candidates against.
        """
        ret = []
        if requirement.name in self._packages_by_name_:
            for package in self._packages_by_name_[requirement.name]:
                if requirement.matches(package.version):
                    ret.append(package)
        return ret

    @no_dirty
    def package_id(self, package):
        """ Returns the 'package id' of the given package."""
        try:
            return self._package_to_id_[package]
        except KeyError:
            msg = "Package {0!r} not found in the pool.".format(package)
            raise ValueError(msg)

    @no_dirty
    def id_to_package(self, package_id):
        """ Returns the package of the given 'package id'."""
        try:
            return self._id_to_package_[package_id]
        except KeyError:
            msg = "Package ID {0!r} not found in the pool.".format(package_id)
            raise ValueError(msg)

    @no_dirty
    def id_to_string(self, package_id):
        """
        Convert a package id to a nice string representation.
        """
        package = self._id_to_package_[abs(package_id)]
        package_string = package.name + "-" + str(package.version)
        if package_id > 0:
            return "+" + package_string
        else:
            return "-" + package_string

    @no_dirty
    def name_to_packages(self, name):
        return tuple(self._packages_by_name_[name])

    @property
    @no_dirty
    def package_ids(self):
        return tuple(self._id_to_package_.keys())

    def _prepare_packages(self):
        modifiers = self._modifiers
        all_packages = itertools.chain.from_iterable(self._repositories)
        self._reset_packages()
        for current_id, package in enumerate(all_packages, start=1):
            package = package.clone_with_modifiers(modifiers)
            self._id_to_package_[current_id] = package
            self._package_to_id_[package] = current_id
            self._packages_by_name_[package.name].append(package)
