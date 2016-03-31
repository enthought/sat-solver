from collections import defaultdict

from simplesat import Pool
from simplesat.utils.graph import (package_lit_dependency_graph,
                                   transitive_neighbors)


def _compute_dependency_dict(pool, package_ids):
    """ Return mapping of nodes to their dependents. """
    graph = package_lit_dependency_graph(pool, package_ids, closed=False)
    neighbors = transitive_neighbors(graph)
    return neighbors


def _reverse_mapping(mapping):
    reversed_map = defaultdict(set)
    for key, vals in mapping.iteritems():
        for v in vals:
            reversed_map[v].add(key)

    return reversed_map


def _dependencies_for_requirement(pool, neighbor_mapping, requirement):
    result_dependencies = set()
    for package in pool.what_provides(requirement):
        package_id = pool.package_id(package)
        dependency_ids = neighbor_mapping[package_id]
        result_dependencies.update(pool.id_to_package(d_id)
                                   for d_id in dependency_ids)

    return result_dependencies


def _package_ids_from_repositories(pool, repositories):
    return set(pool.package_id(pkg) for repo in repositories for pkg in repo)


def compute_dependencies(repositories, requirement, transitive=False):
    """ Compute packages in the given repos on which `requirement` depends.

    Parameters
    ----------------
    repositories : iterable of Repository objects
    requirement : Requirement
        The package requirement for which to compute dependencies.

    Returns
    -----------
    dependencies : set
        Set of packages in the pool that the given package depends on
    """
    pool = Pool(repositories)
    package_ids = _package_ids_from_repositories(pool, repositories)
    neighbors = _compute_dependency_dict(pool, package_ids)
    dependencies = _dependencies_for_requirement(pool, neighbors, requirement)
    return dependencies


def compute_reverse_dependencies(repositories, requirement, transitive=False):
    """ Compute packages in the given pool that depend on the given requirement

    Parameters
    ----------------
    repositories : iterable of Repository objects
    requirement : Requirement
        The package requirement for which to compute reverse dependencies.

    Returns
    -----------
    dependencies : set
         Set of packages in the pool that depend on the given requirement.
    """
    pool = Pool(repositories)
    package_ids = _package_ids_from_repositories(pool, repositories)
    neighbors = _compute_dependency_dict(pool, package_ids)
    reverse_neighbors = _reverse_mapping(neighbors)
    dependencies = _dependencies_for_requirement(pool, reverse_neighbors,
                                                 requirement)
    return dependencies
