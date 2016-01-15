import re

from okonomiyaki.versions import EnpkgVersion

from simplesat.package import PackageMetadata
from .kinds import Any, EnpkgUpstreamMatch, Equal
from .parser import _DISTRIBUTION_R, _VERSION_R, _WS_R, _RawRequirementParser


DEPENDS_RE = re.compile("depends\s*\((.*)\)")
CONFLICTS_RE = re.compile("conflicts\s*\((.*)\)")

_MAYBE_WS_R = " *"
_DISTRIBUTION_R = "(?P<distribution>{})".format(_DISTRIBUTION_R)
_VERSION_R = "(?P<version>{})".format(_VERSION_R)
_CONSTRAINT = "(?P<constraint>[^,]*)"

CONSTRAINT_BLOCK_RC = re.compile("(?P<kind>\w+)\s*\((?P<constraints>.*?)\)")
PACKAGE_RC = re.compile(_DISTRIBUTION_R + _WS_R + _VERSION_R)
CONSTRAINT_RC = re.compile(_DISTRIBUTION_R + _MAYBE_WS_R + _CONSTRAINT)

VALID_CONSTRAINT_KINDS = (
    "install_requires",
)
CONSTRAINT_SYNONYMS = {
    'depends': 'install_requires'
}


class PrettyPackageStringParser2(object):

    def __init__(self, version_factory):
        self._version_factory = version_factory

    def parse(self, pretty_string):
        """Return the dict representation of the pretty package string.

        Pretty package strings are of the form::

            numpy 1.8.1-1; install_requires (MKL == 10.3, nose ^= 1.3.4); conflicts (numeric)  # noqa
        """
        pkg = {}

        try:
            preamble, constraints_blocks = pretty_string.rsplit(";", 1)
        except ValueError:
            preamble = pretty_string
            constraints_blocks = ''

        for match in CONSTRAINT_BLOCK_RC.finditer(constraints_blocks):
            kind = match.group('kind')
            kind = CONSTRAINT_SYNONYMS.get(kind, kind)
            constraints_str = match.group('constraints')
            if kind not in VALID_CONSTRAINT_KINDS:
                msg = "Invalid package string. Unknown constraint kind: {!r}"
                raise ValueError(msg.format(kind))
            constraints = {}
            for match in CONSTRAINT_RC.finditer(constraints_str):
                dist = match.group('distribution')
                constraint_str = match.group('constraint')
                constraints.setdefault(dist, [[]])[0].append(constraint_str)
            pkg[kind] = constraints

        # Turn constraints into immutable nested tuples
        pkg = {
            kind: tuple(
                (dist, tuple(tuple(clist) for clist in constraint_lists))
                for dist, constraint_lists in sorted(dist_constraints.items())
            )
            for kind, dist_constraints in pkg.items()
        }

        distribution, version = _parse_preamble(preamble)
        pkg["distribution"] = distribution
        pkg["version"] = self._version_factory(version)

        return pkg

    def parse_to_package(self, package_string):
        """ Parse the given pretty package string.

        Parameters
        ----------
        package_string : str
            The pretty package string, e.g.
            "numpy 1.8.1-1; depends (MKL == 10.3, nose ^= 1.3.4)"

        Returns
        -------
        package : PackageMetadata
        """
        pkg_dict = self.parse(package_string)
        distribution = pkg_dict.pop('distribution')
        version = pkg_dict.pop('version')
        return PackageMetadata(distribution, version, **pkg_dict)


class PrettyPackageStringParser(object):
    """ Parser for pretty package strings.

    Pretty package strings are of the form::

        numpy 1.8.1-1; depends (MKL == 10.3, nose ^= 1.3.4)
    """
    def __init__(self, version_factory):
        self._parser = _RawRequirementParser()
        self._version_factory = version_factory

    def parse(self, package_string):
        """ Parse the given pretty package string.

        Parameters
        ----------
        package_string : str
            The pretty package string, e.g.
            "numpy 1.8.1-1; depends (MKL == 10.3, nose ^= 1.3.4)"

        Returns
        -------
        name : str
            The package name
        version : version object
            The package version
        install_requires : dict
            A dict mapping a package name to a set of constraints mapping.
        """
        version_factory = self._version_factory

        parts = package_string.split(";")

        name, version_string = _parse_preamble(parts[0])

        constraints = {}

        for part in parts[1:]:
            part = part.lstrip()

            for kind, r in (("install_requires", DEPENDS_RE),):
                m = r.search(part)
                if m is not None:
                    break
            else:
                msg = "Invalid constraint block: '{0}'".format(part)
                raise ValueError(msg)

            constraints[kind] = dict(
                self._parser.parse(m.group(1), version_factory)
            )

        return (name, version_factory(version_string),
                constraints.get("install_requires", {}))

    def parse_to_package(self, package_string):
        """ Parse the given pretty package string.

        Parameters
        ----------
        package_string : str
            The pretty package string, e.g.
            "numpy 1.8.1-1; depends (MKL == 10.3, nose ^= 1.3.4)"

        Returns
        -------
        package : PackageMetadata
        """
        name, version, install_requires = \
            self.parse_to_legacy_constraints(package_string)
        return PackageMetadata(name, version, install_requires)

    def parse_to_legacy_constraints(self, package_string):
        """ Parse the given package string into a name, version and a set of
        legacy requirement as used by our index format v1 (e.g. 'MKL 10.3-1'
        for exact dependency to MKL 10.3-1).

        """
        name, version, install_requires = self.parse(package_string)

        legacy_constraints = []
        for dependency_name, constraints in install_requires.items():
            assert len(constraints) == 1, constraints
            constraint = next(iter(constraints))
            assert isinstance(constraint,
                              (EnpkgUpstreamMatch, Any, Equal))
            if isinstance(constraint, Any):
                legacy_constraint = dependency_name
            elif isinstance(constraint, Equal):
                legacy_constraint = (dependency_name + ' ' +
                                     str(constraint.version))
            else:  # EnpkgUpstreamMatch
                assert isinstance(constraint.version, EnpkgVersion)
                legacy_constraint = (dependency_name + ' ' +
                                     str(constraint.version.upstream))
            legacy_constraints.append(legacy_constraint)

        return name, version, tuple(legacy_constraints)


def constraints_to_pretty_string(constraints):
    """ Given a set of constraints, returns a pretty string."""
    data = []

    for name, constraints_set in constraints:
        for constraint in constraints_set:
            constraint_str = str(constraint)
            if len(constraint_str) > 0:
                data.append(name + " " + constraint_str)
            else:
                data.append(name)

    return ", ".join(data)


def legacy_dependencies_to_pretty_string(install_requires):
    """ Convert a sequence of legacy dependency strings to a pretty constraint
    string.

    Parameters
    ----------
    install_requires : seq
        Sequence of legacy dependency string (e.g. 'MKL 10.3')
    """
    constraints_mapping = []

    for dependency in install_requires:
        name, constraint = _legacy_requirement_string_to_name_constraints(
            dependency
        )
        assert isinstance(constraint, (EnpkgUpstreamMatch, Any, Equal))
        constraints_mapping.append((name, frozenset((constraint,))))

    return constraints_to_pretty_string(constraints_mapping)


def package_to_pretty_string(package):
    """ Given a PackageMetadata instance, returns a pretty string."""
    template = "{0.name} {0.version}"
    if len(package.install_requires) > 0:
        string = legacy_dependencies_to_pretty_string(package.install_requires)
        template += "; depends ({0})".format(string)
    return template.format(package)


def _parse_preamble(preamble):
    parts = preamble.strip().split()
    if not len(parts) == 2:
        raise ValueError("Invalid preamble: {0!r}".format(preamble))
    else:
        return parts[0], parts[1]


def _legacy_requirement_string_to_name_constraints(requirement_string):
    """ Creates a requirement from a legacy requirement string (as found
    in our current egg metadata, format < 2).

    Parameters
    ----------
    requirement_string : str
        The legacy requirement string, e.g. 'MKL 10.3'
    """
    parts = requirement_string.split(None, 1)
    if len(parts) == 2:
        name, version_string = parts
        version = EnpkgVersion.from_string(version_string)
        if version.build == 0:
            return name, EnpkgUpstreamMatch(version)
        else:
            return name, Equal(version)
    elif len(parts) == 1:
        name = parts[0]
        return name, Any()
    else:
        raise ValueError(parts)
