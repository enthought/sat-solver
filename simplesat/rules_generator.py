import collections
import enum

from enstaller.errors import EnstallerException

from enstaller.new_solver.requirement import Requirement
from enstaller.solver import JobType


class RuleType(enum.Enum):
    internal_allow_update = 1
    job_install = 2
    job_remove = 3
    job_update = 4
    package_requires = 7
    package_same_name = 10
    package_implicit_obsoletes = 11
    package_installed = 12

    internal = 256


class PackageRule(object):
    @classmethod
    def _from_string(cls, rule_string, pool):
        """
        Creates a PackageRule from a rule string, e.g. '-numpy-1.6.0 | numpy-1.7.0'

        Because package full name -> id is not 1-to-1 mapping, this may fail
        when a package has multiple ids. This is mostly used for testing, to
        write reference rules a bit more easily.
        """
        packages_string = (s.strip() for s in rule_string.split("|"))
        package_literals = []
        for package_string in packages_string:
            if package_string.startswith("-"):
                positive = False
                package_string = package_string[1:]
            else:
                positive = True

            requirement = Requirement.from_package_string(package_string)
            package_candidates = pool.what_provides(requirement)
            if len(package_candidates) == 0:
                msg = "No candidate for package {0!r}".format(package_string)
                raise EnstallerException(msg)
            elif len(package_candidates) > 1:
                msg = "> 1 candidate for package {0!r} requirement, cannot " \
                      "create rule from it" % package_string
                raise EnstallerException(msg)
            else:
                _id = pool.package_id(package_candidates[0])
                if positive:
                    package_literals.append(_id)
                else:
                    package_literals.append(-_id)
        return cls(package_literals)

    def __init__(self, literals, reason):
        self.literals = tuple(sorted(literals))
        self._reason = RuleType(reason)

    @property
    def is_assertion(self):
        return len(self.literals) == 1

    @property
    def reason(self):
        return self._reason

    def to_string(self, pool):
        parts = [pool.id_to_string(literal) for literal in self.literals]
        s = " | ".join(parts)

        if self._reason == RuleType.job_install:
            return "Install command rule ({})".format(s)
        elif self._reason == RuleType.job_update:
            return "Update to latest command rule ({})".format(s)
        elif self._reason == RuleType.job_remove:
            return "Remove command rule ({})".format(s)
        elif self._reason == RuleType.package_same_name:
            parts = [pool.id_to_string(abs(literal))
                     for literal in self.literals]
            s = " | ".join(parts)
            return "Can only install one of: ({})".format(s)
        elif self._reason == RuleType.package_installed:
            parts = [pool.id_to_string(abs(literal))
                     for literal in self.literals]
            s = " | ".join(parts)
            return "Should install one of: ({})".format(s)
        elif self._reason == RuleType.package_requires:
            source_id = abs(self.literals[0])
            source = pool._id_to_package[source_id]
            parts = [pool.id_to_string(literal)
                     for literal in self.literals[1:]]
            s = " | ".join(parts)
            return "{} {} requires ({})".format(source.name, source.version, s)
        else:
            return s

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.literals == other.literals)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.literals)


class RulesGenerator(object):
    def __init__(self, pool, request, installed_map=None):
        self._rules_set = collections.OrderedDict()
        self._pool = pool

        self.request = request
        self.installed_map = installed_map or collections.OrderedDict()
        self.added_package_ids = set()

    def iter_rules(self):
        """
        Return an iterator over each created rule.
        """
        self.added_package_ids = set()
        for package in self.installed_map.values():
            self._add_installed_package_rules(package)
            self._add_package_rules(package)
        self._add_job_rules()
        return self._rules_set

    # ------------------------------
    # API to create individual rules
    # ------------------------------
    def _create_dependency_rule(self, package, dependencies, reason,
                                reason_details=""):
        """
        Create the rule for the dependencies of a package.

        This dependency is of the form (-A | R1 | R2 | R3) where R* are
        the set of packages provided by the dependency requirement.

        Parameters
        ----------
        package: PackageInfo
            The package with a requirement
        dependencies: sequence
            Sequence of packages that fulfill the requirement.
        reason: str
            A valid PackageRule.reason value
        reason_details: str
            Optional details explaining that rule origin.

        Returns
        -------
        rule: PackageRule or None
        """
        literals = [-self._pool.package_id(package)]

        for dependency in dependencies:
            if dependency != package:
                literals.append(self._pool.package_id(dependency))

        return PackageRule(literals, reason)

    def _create_conflicts_rule(self, issuer, provider, reason, reason_details=""):
        """
        Create a conflict rule between issuer and provider

        The rule is of the form (-A | -B)

        Parameters
        ----------
        issuer: PackageInfo
            Package declaring the conflict
        provider: PackageInfo
            Package causing the conflict
        reason: str
            One of PackageRule.reason
        reason_details: str
            Optional details explaining that rule origin.

        Returns
        -------
        rule: PackageRule or None
        """
        if issuer != provider:
            return PackageRule([-self._pool.package_id(issuer),
                                -self._pool.package_id(provider)], reason)

    def _create_install_one_of_rule(self, packages, reason):
        """
        Creates a rule to Install one of the given packages.

        The rule is of the form (A | B | C)

        Parameters
        ----------
        packages: sequence
            List of packages to choose from
        reason: str
            One of PackageRule.reason

        Returns
        -------
        rule: PackageRule
        """
        literals = [self._pool.package_id(p) for p in packages]
        return PackageRule(literals, reason)

    def _create_remove_rule(self, package, reason):
        """
        Create the rule to remove a package.

        For a package A, the rule is simply (-A)

        Parameters
        ----------
        package: PackageInfo
            The package with a requirement

        Returns
        -------
        rule: PackageRule or None
        """
        return PackageRule((-self._pool.package_id(package),), reason)

    # -------------------------------------------------
    # API to assemble individual rules from requirement
    # -------------------------------------------------
    def _add_rule(self, rule, rule_type):
        """
        Add the given rule to the internal rules set.

        Does nothing if the rule is None.

        Parameters
        ----------
        rule: PackageRule or None
            The rule to add
        rule_type: str
            Rule's  type
        """
        if rule is not None and rule not in self._rules_set:
            self._rules_set[rule] = None

    def _add_dependencies_rules(self, package, work_queue):
        for dependency in package.dependencies:
            requirement = Requirement.from_legacy_requirement_string(dependency)
            dependency_candidates = self._pool.what_provides(requirement)

            assert len(dependency_candidates) > 0, \
                ("No candidates found for requirement {0!r}, needed for "
                 "dependency {1!r}".format(requirement.name, package))

            rule = self._create_dependency_rule(package, dependency_candidates,
                                                RuleType.package_requires,
                                                str(dependency))
            self._add_rule(rule, "package")

            for candidate in dependency_candidates:
                work_queue.append(candidate)

    def _add_package_rules(self, package):
        """
        Create all the rules required to satisfy installing the given package.
        """
        work_queue = collections.deque()
        work_queue.append(package)

        while len(work_queue) > 0:
            p = work_queue.popleft()

            p_id = self._pool.package_id(p)
            if p_id not in self.added_package_ids:
                self.added_package_ids.add(p_id)
                self._add_dependencies_rules(p, work_queue)

                requirement = Requirement.from_legacy_requirement_string(p.name)
                obsolete_providers = self._pool.what_provides(requirement)
                for provider in obsolete_providers:
                    if provider != p:
                        if provider.name == p.name:
                            reason = RuleType.package_same_name
                        else:
                            reason = RuleType.package_implicit_obsoletes
                        rule = self._create_conflicts_rule(p, provider,
                                                           reason, str(p))
                        self._add_rule(rule, "package")

    def _add_install_job_rules(self, job):
        packages = self._pool.what_provides(job.requirement)
        if len(packages) > 0:
            for package in packages:
                if package not in self.installed_map:
                    self._add_package_rules(package)

            rule = self._create_install_one_of_rule(packages,
                                                    RuleType.job_install)
            self._add_rule(rule, "job")

    def _add_remove_job_rules(self, job):
        packages = self._pool.what_provides(job.requirement)
        for package in packages:
            rule = self._create_remove_rule(package, RuleType.job_remove)
            self._add_rule(rule, "job")

    def _add_update_job_rules(self, job):
        """
        Create rules that force the update of the package by requiring all of
        the standard rules then adding an additional rule for just the most
        recent version.
        """
        packages = self._pool.what_provides(job.requirement)
        if len(packages) == 0:
            return
        # An update request *must* install the latest package version
        def key(package):
            installed = self._pool.package_id(package) in self.installed_map
            return (package.version, installed)
        package = max(packages, key=key)
        self._add_package_rules(package)
        rule = PackageRule(
            (self._pool.package_id(package),),
            RuleType.job_update
        )
        self._add_rule(rule, "job")

    def _add_installed_package_rules(self, package):
        packages_all_versions = self._pool._packages_by_name[package.name]
        for other in packages_all_versions:
            self._add_package_rules(other)

    def _add_job_rules(self):
        for job in self.request.jobs:
            if job.kind == JobType.install:
                self._add_install_job_rules(job)
            elif job.kind == JobType.remove:
                self._add_remove_job_rules(job)
            elif job.kind == JobType.update:
                self._add_update_job_rules(job)
            else:
                msg = "Job kind {0!r} not supported".format(job.kind)
                raise NotImplementedError(msg)
