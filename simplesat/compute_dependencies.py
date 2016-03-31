from simplesat.utils.graph import (package_lit_dependency_graph,
                                   transitive_neighbors)


def compute_dependencies(pool, requirement, transitive=False):
    """ Compute packages in the given pool on the given requirement depends

    Parameters
    ----------------
    pool : Pool
    requirement : Requirement
        The package requirement for which to compute dependencies.

    Returns
    -----------
    dependencies : sequence
        Set of packages in the pool that the given package depends on
    """
    package_ids = pool._id_to_package_.keys()
    graph = package_lit_dependency_graph(pool, package_ids, closed=False)
    neighbors = transitive_neighbors(graph)

    result_dependencies = set()
    for package in pool.what_provides(requirement):
        package_id = pool.package_id(package)
        dependency_ids = neighbors[package_id]
        for d_id in dependency_ids:
            result_dependencies.add(pool.id_to_package(d_id))

    return result_dependencies
