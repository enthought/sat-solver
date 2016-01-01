import re

import six

from okonomiyaki.versions import EnpkgVersion

from .constraints import MultiConstraints
from .constraints.kinds import Any, EnpkgUpstreamMatch, Equal
from .constraints.package_parser import (
    _legacy_requirement_string_to_name_constraints
)
from .constraints.parser import _RawRequirementParser
from .errors import InvalidDependencyString, SolverException


_FULL_PACKAGE_RE = re.compile("""\
                              (?P<name>[^-.]+)
                              -
                              (?P<version>(.*))
                              $""", re.VERBOSE)


def parse_package_full_name(full_name):
    """
    Parse a package full name (e.g. 'numpy-1.6.0-1') into a (name,
    version_string) pair.
    """
    m = _FULL_PACKAGE_RE.match(full_name)
    if m:
        return m.group("name"), m.group("version")
    else:
        msg = "Invalid package full name {0!r}".format(full_name)
        raise SolverException(msg)


def _first(iterable):
    return six.next(iter(iterable))


class Requirement(object):
    """Requirements instances represent a 'package requirement', that is a
    package + version constraints.

    Arguments
    ---------
    name: str
        PackageInfo name
    specs: seq
        Sequence of constraints
    """
    @classmethod
    def _from_string(cls, string,
                     version_factory=EnpkgVersion.from_string):
        """ Creates a requirement from a requirement string.

        Parameters
        ----------
        requirement_string : str
            The requirement string, e.g. 'MKL >= 10.3, MKL < 11.0'
        """
        parser = _RawRequirementParser()
        named_constraints = parser.parse(string, version_factory)
        if len(named_constraints) > 1:
            names = named_constraints.keys()
            msg = "Multiple package name for constraint: {0!r}".format(names)
            raise InvalidDependencyString(msg)
        assert len(named_constraints) > 0
        name = _first(named_constraints.keys())
        return cls(name, named_constraints[name])

    @classmethod
    def from_legacy_requirement_string(cls, requirement_string,
                                       version_factory=EnpkgVersion.from_string):
        """ Creates a requirement from a legacy requirement string (as
        found in our current egg metadata, format < 2).

        Parameters
        ----------
        requirement_string : str
            The legacy requirement string, e.g. 'MKL 10.3'
        """
        name, constraint = _legacy_requirement_string_to_name_constraints(
            requirement_string
        )
        return cls(name, [constraint])

    @classmethod
    def from_package_string(cls, package_string,
                            version_factory=EnpkgVersion.from_string):
        """ Creates a requirement from a package full version.

        Parameters
        ----------
        package_string : str
            The package string, e.g. 'numpy-1.8.1-1'
        """
        name, version_string = parse_package_full_name(package_string)
        version = version_factory(version_string)
        return cls(name, [Equal(version)])

    def __init__(self, name, constraints=None):
        self.name = name

        self._constraints = MultiConstraints(constraints)

    def matches(self, version_candidate):
        """ Returns True if the given version matches this set of
        requirements, False otherwise.

        Parameters
        ----------
        version_candidate : obj
            A valid version object (must match the version factory of the
            requirement instance).
        """
        return self._constraints.matches(version_candidate)

    def __eq__(self, other):
        return (self.name == other.name
                and self._constraints == other._constraints)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.name, self._constraints))

    def __str__(self):
        parts = []
        for constraint in self._constraints._constraints:
            if not isinstance(constraint, Any):
                parts.append(str(constraint))

        if len(parts) == 0:
            return self.name
        else:
            return self.name + " " + ", ".join(parts)

    @property
    def has_any_version_constraint(self):
        """ True if there is any version constraint."""
        constraints = self._constraints._constraints
        if len(constraints) == 0:
            return False
        elif len(constraints) == 1:
            constraint = six.next(iter(constraints))
            if isinstance(constraint, Any):
                return False
        return True


class _LegacyRequirement(object):
    @classmethod
    def from_requirement_string(cls, requirement_string):
        """ Creates a requirement from a legacy requirement string (as
        found in our current egg metadata, format < 2).

        Parameters
        ----------
        requirement_string : str
            The legacy requirement string, e.g. 'MKL 10.3'
        """
        ret = Requirement.from_legacy_requirement_string(
            requirement_string, EnpkgVersion.from_string
        )
        return cls(ret)

    def __init__(self, requirement):
        self._requirement = requirement

    def matches(self, arg):
        return self._requirement.matches(arg)

    @property
    def name(self):
        return self._requirement.name.lower()

    @property
    def as_dict(self):
        d = {"name": self.name}
        if self._strictness >= 2:
            constraint = six.next(iter(
                self._requirement._constraints._constraints
            ))
            d["version"] = str(constraint.version.upstream)
            if self._strictness == 3:
                d["build"] = str(constraint.version.build)

        return d

    @property
    def strictness(self):
        constraints = self._requirement._constraints._constraints
        if len(constraints) == 0:
            return 1
        elif len(constraints) == 1:
            constraint = six.next(iter(constraints))
            if isinstance(constraint, Any):
                return 1
            elif isinstance(constraint, EnpkgUpstreamMatch):
                return 2
            elif isinstance(constraint, Equal):
                return 3
            else:
                raise RuntimeError(
                    "Constraint {0!r} cannot be used in requirement used for "
                    "legacy solver".format(constraint)
                )
        else:
            raise RuntimeError(
                "Complex requirement cannot be used in legacy solver"
            )

    def __str__(self):
        if self.strictness == 0:
            return ''
        res = self.name
        if self.strictness >= 2:
            constraint = six.next(iter(
                self._requirement._constraints._constraints
            ))
            res += ' %s' % str(constraint.version.upstream)
            if self.strictness == 3:
                res += '-%d' % constraint.version.build
        return res

    def __eq__(self, other):
        return self._requirement == other._requirement

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self._requirement)

