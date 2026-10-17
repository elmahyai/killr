"""Size (number of edges) of an igraph graph.

``gsize`` is ``ecount``. Both call ``ecount_impl``, which checks the
argument with ``ensure_igraph`` and then reads ``igraph_ecount``. That
count is the length of the ``from`` vector on the external pointer.
The result is already a length-1 double.

A current graph is a list of length 10 whose last element is an
environment. A live pointer keeps the edge count that was stored with
it, so a rewritten ``from`` slot does not change the result. When the
pointer is missing, the count is the length of the numeric ``from``
slot after the same restore ``gorder`` runs: the vertex count and the
edge ends are checked, and only then is that length kept. A ``from``
or ``to`` vector that still has to read the pointer fails before those
ends are copied.
"""

from __future__ import annotations

from igraph.gorder import (
    Environment,
    IgraphError,
    Int,
    Real,
    _inherits_igraph,
    _logical0,
    _real0,
    gorder,
)


_MISSING = object()

_EXTERNAL_POINTER = (
    "R_ExternalPtrAddr: argument of type NILSXP is not an external pointer"
)


class LazyEnds:
    """An edge-end vector whose length still reads the external pointer."""


def _lazy_restore(graph) -> bool:
    """True when restore would read an end vector through a null pointer."""

    if graph is _MISSING or graph is None:
        return False
    if not _inherits_igraph(graph):
        return False
    length = getattr(graph, "length", None)
    if length == 10 and getattr(graph, "atomic", None) == "integer":
        return False
    env = getattr(graph, "env", None)
    if length != 10 or not isinstance(env, Environment):
        return False
    if env.pointer is not None:
        return False
    return isinstance(getattr(graph, "from_", None), LazyEnds) or isinstance(
        getattr(graph, "to", None), LazyEnds
    )


def _live_pointer(graph) -> bool:
    env = getattr(graph, "env", None)
    return (
        getattr(graph, "length", None) == 10
        and isinstance(env, Environment)
        and env.pointer is not None
    )


def _from_length(graph) -> int:
    slot = getattr(graph, "from_", None)
    if slot is None:
        return 0
    if isinstance(slot, (Int, Real)):
        return len(slot.values)
    return 0


def gsize(graph=_MISSING):
    """Return the number of edges in ``graph`` as a length-1 double."""

    if graph is _MISSING:
        gorder()
    if _lazy_restore(graph):
        _real0(graph.n_slot)
        _logical0(graph.directed)
        raise IgraphError(_EXTERNAL_POINTER)
    live = _live_pointer(graph)
    gorder(graph)
    if live:
        return float(graph.env.edges)
    count = _from_length(graph)
    graph.env.edges = count
    return float(count)
