from collections import defaultdict

from simplesat import Pool
from simplesat.utils.graph import (package_lit_dependency_graph,
                                   transitive_neighbors)


def _compute_dependency_dict(pool, package_ids, transitive=False):
    """ Return mapping of nodes to their dependents. """
    neighbors = package_lit_dependency_graph(pool, package_ids, closed=False)
    if transitive:
        neighbors = transitive_neighbors(neighbors)
    return neighbors


def _reverse_mapping(mapping):
    reversed_map = defaultdict(set)
    for key, vals in mapping.iteritems():
        for v in vals:
            reversed_map[v].add(key)

    return reversed_map


def _dependencies_for_requirement(pool, neighbor_mapping, requirement):
    result_dependencies = set()
    for package_id in _package_ids_satisfying_requirement(pool, requirement):
        dependency_ids = neighbor_mapping[package_id]
        result_dependencies.update(pool.id_to_package(d_id)
                                   for d_id in dependency_ids)

    return result_dependencies


def _package_ids_satisfying_requirement(pool, requirement):
    for package in pool.what_provides(requirement):
        yield pool.package_id(package)


def _package_ids_from_repositories(pool, repositories):
    return set(pool.package_id(pkg) for repo in repositories for pkg in repo)


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
        Set of packages in the pool that the given package depends on
    """
    pool = Pool(repositories)
    package_ids = _package_ids_from_repositories(pool, repositories)
    neighbors = _compute_dependency_dict(pool, package_ids, transitive)
    dependencies = _dependencies_for_requirement(pool, neighbors, requirement)
    return dependencies


def compute_reverse_dependencies(repositories, requirement, transitive=False):
    """ Compute packages in the given pool that depend on the given requirement

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
         Set of packages in the pool that depend on the given requirement.
    """
    pool = Pool(repositories)
    package_ids = _package_ids_from_repositories(pool, repositories)

    neighbors = _compute_dependency_dict(pool, package_ids, transitive)
    reverse_neighbors = _reverse_mapping(neighbors)
    dependencies = _dependencies_for_requirement(pool, reverse_neighbors,
                                                 requirement)
    return dependencies
