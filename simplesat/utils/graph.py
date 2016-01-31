# -*- coding: utf-8 -*-

from collections import deque


def connected_nodes(node, neighbor_func, visited=None):
    """ Recursively build up a set of nodes connected to `node` by following
    neighbors as given by `neighbor_func(node)`. """
    visited = set() if visited is None else visited
    queue = set([node])
    while queue:
        node = queue.pop()
        visited.add(node)
        neighbors = neighbor_func(node) - visited
        queue.update(neighbors)
    return visited


def backtrack(end, start, visited):
    """ Return a list of nodes from `start` to `end` by recursively looking up
    the current node in `visited`. `visited` is a dictionary of one-way edges
    between nodes.
    """
    path = [end]
    node = end
    while node != start:
        node = visited[node]
        path.append(node)
    return list(reversed(path))


def breadth_first_search(start, neighbor_func, terminate_func, visited=None):
    """
    Return a path from `start` to `end` such that `terminate_func(end)` is
    True by following neighbors as given by `neighborfunc(node)`.

    `visited` is used both to track the current path and to avoid recomputing
    sections of the graph that have been visited before.
    """
    queue = deque([start])
    visited = {} if visited is None else visited
    visited[start] = None
    while queue:
        node = queue.popleft()
        if terminate_func(node):
            return backtrack(node, start, visited), visited
        for neighbor in neighbor_func(node):
            if neighbor in visited:
                continue
            queue.append(neighbor)
            visited[neighbor] = node
    return [], visited
