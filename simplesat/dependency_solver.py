import collections

import six

from simplesat.constraints.requirement import InstallRequirement
from simplesat.errors import NoPackageFound, SatisfiabilityError
from simplesat.pool import Pool
from simplesat.repository import Repository
from simplesat.request import JobType, Request
from simplesat.rules_generator import RulesGenerator
from simplesat.sat.policy import InstalledFirstPolicy
from simplesat.sat import MiniSATSolver
from simplesat.transaction import Transaction
from simplesat.utils import timed_context, connected_nodes


def requirements_from_repository(repository):
    """
    Return a list of requirements, one to match each package in `repository`.

    Parameters
    ----------
    repository : Repository
        The repository for which to generate requirements.

    Returns
    -------
    list of Requirement
        The matching requirements.
    """
    R = InstallRequirement.from_package_string
    return tuple(R("{0.name}-{0.version}".format(package))
                 for package in repository)


def repository_from_requirements(repositories, requirements, modifiers=None):
    """
    Return a new repository that only has packages explicitly mentioned in the
    requirements.

    Parameters
    ----------
    repositories : list of Repository
        The list of repositories to draw packages from.
    requirements : list of Requirement
        The requirements used to identify relevent packages. All packages that
        satisfy any of the requirements will be included.
    modifiers : ConstraintModifiers, optional
        If not None, modify requirements before resolving packages.

    Returns
    -------
    Repository
        A repository containing the relevant packages.
    """
    pool = Pool(repositories, modifiers=modifiers)
    listed_packages = set()
    for requirement in requirements:
        listed_packages.update(pool.what_provides(requirement))
    return Repository(listed_packages)


def repository_is_consistent(repository, modifiers=None):
    """
    Return True if all packages in a repository can be installed together.

    .. Note::
        Any repository with more than one version of a package will return
        False because we only permit one version of a package to be installed
        at a time.

    Parameters
    ----------
    repository : Repository
        The repository to draw packages from.
    modifiers : ConstraintModifiers, optional
        If not None, modify requirements before resolving packages.

    Returns
    -------
    bool
        True if every package in the repository can be installed
        simultaneously, otherwise False.
    """
    requirements = requirements_from_repository(repository)
    return requirements_are_satisfiable(
        [repository], requirements, modifiers=modifiers)


def requirements_are_complete(repositories, requirements, modifiers=None):
    """
    Return True if the list of requirements includes all required transitive
    dependencies. I.e. it will report whether all packages that are needed are
    explicitly required.

    Parameters
    ----------
    repositories : list of Repository
        The list of repositories to draw packages from.
    requirements : list of Requirement
        The requirements used to identify relevent packages.
    modifiers : ConstraintModifiers, optional
        If not None, modify requirements before resolving packages.

    Returns
    -------
    bool
        True if the requirements specify all necessary packages.
    """
    repo = repository_from_requirements(repositories, requirements)
    return requirements_are_satisfiable(
        [repo], requirements, modifiers=modifiers)


def requirements_are_satisfiable(repositories, requirements, modifiers=None):
    """ Determine if the list of requirements can be satisfied together.

    Parameters
    ----------
    repositories : list of Repository
        The list of repositories to draw packages from.
    requirements : list of Requirement
        The requirements used to identify relevent packages.
    modifiers : ConstraintModifiers, optional
        If not None, modify requirements before resolving packages.

    Returns
    -------
    bool
        Return True if the `requirements` can be satisfied by the packages in
        `repositories`.
    """
    request = Request()
    for requirement in requirements:
        request.install(requirement)
    pool = Pool(repositories, modifiers=modifiers)

    try:
        DependencySolver(pool, repositories, []).solve(request)
        return True
    except (SatisfiabilityError, NoPackageFound):
        return False


class DependencySolver(object):

    """
    Top-level class for resolving a package management scenario.

    The solver is configured at construction time with packages repositories
    and a :class:`Policy` and exposes an API for computing a
    :class:`Transaction` that describes what to do.

    Parameters
    ----------
    pool : Pool
        Pool against which to resolve Requirements.
    remote_repositories : list of Repository
        Repositories containing package available for installation.
    installed_repository : Repository
        Repository containing the packages which are currently installed.
    policy : Policy, optional
        The policy for suggesting new packages during the search phase. If none
        is given, then ``simplsat.policy.InstalledFirstPolicy`` is used.
    use_pruning : bool, optional
        When True, attempt to prune package operations that are not strictly
        necessary for meeting the requirements. Without this, packages whose
        assignments have changed as an artefact of the search process, but
        which are not needed for the solution will be modified.

        A typical example might be the installation of a dependency for a
        package that was proposed but later backtracked away.
    strict : bool, optional
        When true, behave more harshly when dealing with broken packages. INFO
        level log messages become WARNINGs and missing dependencies become
        errors rather than causing the package to be ignored.


    >>> from simplesat.constraints.package_parser import \\
    ...     pretty_string_to_package as P
    >>> numpy1921 = P('numpy 1.9.2-1; depends (MKL 10.2-1)')
    >>> mkl = P('MKL 10.3-1')
    >>> installed_repository = Repository([mkl])
    >>> remote_repository = Repository([mkl, numpy1921])
    >>> request = Request()
    >>> request.install(Requirement.from_string('numpy >= 1.9'))
    >>> request.allow_newer('MKL')
    >>> pool = Pool([installed_repo] + remote_repos)
    >>> pool.modifiers = request.modifiers
    >>> solver = DependencySolver(pool, remote_repos, installed_repo)
    >>> transaction = solver.solve(request)
    """

    def __init__(self, pool, remote_repositories, installed_repository,
                 policy=None, use_pruning=True, strict=False):
        self._pool = pool
        self._installed_repository = installed_repository
        self._remote_repositories = remote_repositories
        self._last_rules_time = timed_context("Generate Rules")
        self._last_solver_init_time = timed_context("Solver Init")
        self._last_solve_time = timed_context("SAT Solve")

        self.strict = strict
        self.use_pruning = use_pruning

        self._policy = policy or InstalledFirstPolicy(
            pool, installed_repository
        )

    def solve(self, request):
        """Given a request return a Transaction that would satisfy it.

        Parameters
        ----------
        request : Request
            The request that should be satisifed.

        Returns
        -------
        Transaction
            The operations to apply to resolve the `request`.

        Raises
        ------
        SatisfiabilityError
            If no resolution is found.

        MissingInstallRequires
            If no packages meet a dependency requirement.
        """
        modifiers = request.modifiers
        self._pool.modifiers = modifiers if modifiers.targets else None
        with self._last_rules_time:
            requirement_ids, rules = self._create_rules_and_initialize_policy(
                request
            )
        with self._last_solver_init_time:
            sat_solver = MiniSATSolver.from_rules(rules, self._policy)
        with self._last_solve_time:
            solution = sat_solver.search()
        solution_ids = _solution_to_ids(solution)

        installed_package_ids = set(
            self._pool.package_id(p)
            for p in self._installed_repository
        )

        if self.use_pruning:
            root_ids = installed_package_ids.union(requirement_ids)
            solution_ids = _connected_packages(
                solution_ids, root_ids, self._pool
            )

        return Transaction(self._pool, solution_ids, installed_package_ids)

    def _create_rules_and_initialize_policy(self, request):
        pool = self._pool
        installed_repository = self._installed_repository

        all_requirement_ids = []

        for job in request.jobs:
            assert job.kind in (
                JobType.install, JobType.remove, JobType.update
            ), 'Unknown job kind: {}'.format(job.kind)

            requirement = job.requirement

            providers = tuple(pool.what_provides(
                requirement, use_modifiers=False))
            if len(providers) == 0:
                raise NoPackageFound(requirement, str(requirement))

            if job.kind == JobType.update:
                # An update request *must* install the latest package version
                def key(package):
                    return (package.version, package in installed_repository)
                providers = [max(providers, key=key)]

            requirement_ids = [pool.package_id(p) for p in providers]
            self._policy.add_requirements(requirement_ids)
            all_requirement_ids.extend(requirement_ids)

        installed_package_ids = collections.OrderedDict()
        for package in installed_repository:
            package_id = pool.package_id(package)
            installed_package_ids[package_id] = package

        rules_generator = RulesGenerator(
            pool, request, installed_package_ids=installed_package_ids,
            strict=self.strict)

        return all_requirement_ids, list(rules_generator.iter_rules())


def _connected_packages(solution, root_ids, pool):
    """ Return packages in `solution` which are associated with `root_ids`. """

    # Our strategy is as follows:
    # ... -> pkg.install_requires -> pkg names -> ids -> _id_to_package -> ...

    def get_name(pkg_id):
        return pool.id_to_package(abs(pkg_id)).name

    root_names = {get_name(pkg_id) for pkg_id in root_ids}

    solution_name_to_id = {
        get_name(pkg_id): pkg_id for pkg_id in solution
        if pkg_id > 0
    }

    solution_root_ids = set(
        pkg_id for name, pkg_id in six.iteritems(solution_name_to_id)
        if name in root_names
    )

    def neighborfunc(pkg_id):
        """ Given a pkg id, return the pkg ids of the immediate dependencies
        that appeared in our solution. """
        constraints = pool.id_to_package(pkg_id).install_requires
        neighbors = set(solution_name_to_id[name] for name, _ in constraints)
        return neighbors

    # Each package can root its own independent graph, so we must start at
    # each one individually
    should_include = set()
    for pkg_id in solution_root_ids:
        # We pass in `should_include` to avoid re-walking a subgraph
        nodes = connected_nodes(pkg_id, neighborfunc, should_include)
        should_include.update(nodes)
    assert should_include.issuperset(solution_root_ids)

    # In addition to all updates and additions to root ids, we must also keep
    # all packages newly *excluded* from root_ids
    connected = should_include.union(s for s in solution if abs(s) in root_ids)
    return connected


def _solution_to_ids(solution):
    # Return solution as list of signed integers.
    ids = (pkg_id if value else -pkg_id
           for pkg_id, value in six.iteritems(solution))
    return sorted(ids, key=lambda lit: abs(lit))
