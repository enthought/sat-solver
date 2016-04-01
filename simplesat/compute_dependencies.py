from collections import defaultdict

import six

from simplesat import Pool
from simplesat.utils.graph import (package_lit_dependency_graph,
                                   transitive_neighbors)


def compute_dependencies(repositories, requirement, transitive=False):
    """ Compute packages in the given repos on which `requirement` depends.

    Parameters
    ----------------
    repositories : iterable of Repository objects
    requirement : Requirement
        The package requirement for which to compute dependencies.
    transitive : bool
        If True, recursively walk up the dependency graph. If False (default),
        only returns the packages on which the package directly depends.

    Returns
    -----------
    dependencies : set
        Set of packages in the given repositories that any packages satisfying
        the given requirement depend on.
    """
    pool = Pool(repositories)
    package_ids = _package_ids_from_repositories(pool, repositories)

    neighbors = _compute_dependency_dict(pool, package_ids, transitive)
    dependencies = _neighbors_for_requirement(pool, neighbors, requirement)
    return dependencies


def compute_reverse_dependencies(repositories, requirement, transitive=False):
    """ Compute packages in `repositories` that depend on the given requirement

    Parameters
    ----------------
    repositories : iterable of Repository objects
    requirement : Requirement
        The package requirement for which to compute reverse dependencies.
    transitive : bool
        If True, recursively walk up the dependency graph. If False (default),
        only returns the packages that directly depend on the package.

    Returns
    -----------
    dependencies : set
        Set of packages in the given repositories that depend on any of the
        packages satisfying the given requirement.
    """
    pool = Pool(repositories)
    package_ids = _package_ids_from_repositories(pool, repositories)
    neighbors = _compute_dependency_dict(pool, package_ids, transitive)

    # Reverse mapping so that package ids point to the packages which depend
    # on them
    reverse_neighbors = _reverse_mapping(neighbors)
    dependencies = _neighbors_for_requirement(pool, reverse_neighbors,
                                              requirement)
    return dependencies


def _compute_dependency_dict(pool, package_ids, transitive=False):
    """ Return mapping of package ids to their dependent package ids.

    If transitive is False, a package id will point to only its immediate
    dependencies. Otherwise, the mapping will include all recursive
    dependencies.
    """
    graph = package_lit_dependency_graph(pool, package_ids, closed=False)
    if transitive:
        return transitive_neighbors(graph)
    return graph


def _reverse_mapping(mapping):
    reversed_map = defaultdict(set)
    for key, vals in six.iteritems(mapping):
        for v in vals:
            reversed_map[v].add(key)

    return reversed_map


def _neighbors_for_requirement(pool, neighbor_mapping, requirement):
    """ Compute neighboring packages for all packages satisfying `requirement`

    Parameters
    ----------------
    pool: Pool
    neighbor_mapping : dict
        Mapping from package ids to "neighboring" package ids. These may be,
        for example, the packages which depend on a package or those on which
        the package depends.
    requirement : Requirement
        The package requirement for which to look up neighbors. All packages
        which satisfy the requirement will be used.

    Returns
    -----------
    neighbors : set
         Set of packages in the pool that are neighbors of packages which
         satisfy `requirement`.
    """
    neighbors = set()
    for package_id in _package_ids_satisfying_requirement(pool, requirement):
        neighbor_ids = neighbor_mapping[package_id]
        neighbors.update(pool.id_to_package(d_id) for d_id in neighbor_ids)

    return neighbors


def _package_ids_satisfying_requirement(pool, requirement):
    """ Yield package ids found in `pool` which satisfy `requirement`. """
    for package in pool.what_provides(requirement):
        yield pool.package_id(package)


def _package_ids_from_repositories(pool, repositories):
    """ Return set of package ids in `pool` for all packages in the given repos
    """
    return set(pool.package_id(pkg) for repo in repositories for pkg in repo)
