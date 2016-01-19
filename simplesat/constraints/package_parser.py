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


class PrettyPackageStringParser(object):

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


def install_requires_to_pretty_strings(install_requires):
    """ Convert a sequence of legacy dependency strings to a pretty constraint
    string.

    Parameters
    ----------
    install_requires : seq
        Sequence of legacy dependency string (e.g. 'MKL 10.3')
    """
    flat_strings = [
        "{} {}".format(dist, constraint_string).strip()
        for dist, constraint_string_disjunction in install_requires
        for constraint_string_conjunction in constraint_string_disjunction
        for constraint_string in constraint_string_conjunction
    ]

    return flat_strings


def package_to_pretty_string(package):
    """ Given a PackageMetadata instance, returns a pretty string."""
    template = "{0.name} {0.version}"
    if len(package.install_requires) > 0:
        string = ' '.join(
            install_requires_to_pretty_strings(package.install_requires))
        template += "; depends ({0})".format(string)
    return template.format(package)


def _parse_preamble(preamble):
    parts = preamble.strip().split()
    if not len(parts) == 2:
        raise ValueError("Invalid preamble: {0!r}".format(preamble))
    else:
        return parts[0], parts[1]
