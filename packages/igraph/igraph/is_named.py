"""Whether an igraph graph has a vertex attribute named ``name``.

``is_named`` checks the object, then reports whether ``\"name\"`` is one of
the vertex attribute names. A graph attribute or an edge attribute called
``name`` does not count, and neither does a different spelling. The values
stored under that attribute are not inspected.
"""

from __future__ import annotations


_MISSING = object()


class IgraphError(Exception):
    """An ``is_named`` failure, using R's condition message."""


class _Environment:
    """The graph's environment slot. Only the type is read."""


class Graph:
    """A current igraph graph.

    ``vertex_attr_names`` is the character vector of vertex attribute names.
    ``None`` in that vector is a missing name. A missing vector is empty.
    """

    def __init__(self, vertex_attr_names=(), classes=("igraph",)):
        self.classes = list(classes)
        self.length = 10
        self.env = _Environment()
        self.vertex_attr_names = _as_name_vector(vertex_attr_names)


class LegacyGraph:
    """An object of class igraph that is not a current 10-slot graph."""

    def __init__(self, length, env=False):
        self.classes = ["igraph"]
        self.length = length
        self.env = _Environment() if env else None
        self.vertex_attr_names = []


def _as_name_vector(names):
    if names is None:
        return []
    if isinstance(names, str):
        return [names]
    return list(names)


def _inherits_igraph(graph) -> bool:
    classes = getattr(graph, "classes", None)
    if classes is None:
        return False
    if isinstance(classes, str):
        classes = [classes]
    return "igraph" in classes


def _reject_unreadable(graph) -> None:
    """The pointer check ``is_igraph`` reaches through ``warn_version``."""

    length = getattr(graph, "length", None)
    env = getattr(graph, "env", None)
    if length == 10 and isinstance(env, _Environment):
        return
    if length == 11:
        raise IgraphError(
            "This graph was created by igraph < 0.2.\n"
            "  Upgrading this format is not supported, sorry."
        )
    raise IgraphError(
        "This graph was created by a now unsupported old igraph version.\n"
        "  Call upgrade_graph() before using igraph functions on that object."
    )


def is_named(graph=_MISSING) -> bool:
    """Return whether ``graph`` has a vertex attribute called ``name``."""

    if graph is _MISSING:
        raise IgraphError('argument "graph" is missing, with no default')
    if graph is None:
        raise IgraphError("Must provide a graph object (provided `NULL`).")
    if not _inherits_igraph(graph):
        raise IgraphError(
            "Must provide a graph object (provided wrong object type)."
        )
    _reject_unreadable(graph)
    return "name" in _as_name_vector(getattr(graph, "vertex_attr_names", None))
