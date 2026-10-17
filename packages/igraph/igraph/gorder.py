"""Order (number of vertices) of an igraph graph.

``gorder`` is ``vcount``. Both call ``vcount_impl``, which checks the
argument with ``ensure_igraph`` and then reads ``igraph_vcount``. That
count is the ``n`` field of the external pointer. ``as.numeric`` returns
it as a length-1 double.

A current graph is a list of length 10 whose last element is an
environment. When that environment has no pointer, the count is rebuilt
from the numeric ``n`` slot: the first element is truncated toward zero
to a 64-bit integer, and the edge ends are checked before that count is
kept. A live pointer is used as stored, so a rewritten ``n`` slot does
not change the result.
"""

from __future__ import annotations

import math


_MISSING = object()
_INT64_MIN = -2**63

_NEGATIVE_VERTICES = (
    "Number of vertices must not be negative. Invalid value\n"
    "Source: graph/type_indexededgelist.c:101"
)
_OUT_OF_RANGE = (
    "Out-of-range vertex IDs when adding edges. Invalid vertex ID\n"
    "Source: graph/type_indexededgelist.c:261"
)
_EDGE_ASSERTION = (
    "At vendor/cigraph/src/core/vector.pmt:516 : "
    "Assertion failed: v->stor_begin != NULL. "
    "This is an unexpected igraph error; please report this "
    "as a bug, along with the steps to reproduce it.\n"
    "Please restart your R session to avoid crashes or other surprising behavior."
)
_OLD_TINY = (
    "This graph was created by igraph < 0.2.\n"
    "  Upgrading this format is not supported, sorry."
)
_OLD = (
    "This graph was created by a now unsupported old igraph version.\n"
    "  Call upgrade_graph() before using igraph functions on that object."
)


class IgraphError(Exception):
    """A ``gorder`` failure, using R's condition message."""


class MissingArg:
    """The value produced by ``rlang::missing_arg()``."""


def missing_arg():
    """Return the object ``rlang::missing_arg()`` produces."""

    return MissingArg()


class Environment:
    """The graph environment. ``pointer`` is the vertex count, or missing."""

    def __init__(self, pointer=None):
        self.pointer = pointer


class Real:
    """An R numeric vector."""

    def __init__(self, *values):
        self.values = [float(value) for value in values]


class Int:
    """An R integer vector."""

    def __init__(self, *values):
        self.values = [int(value) for value in values]


class Logical:
    """An R logical vector."""

    def __init__(self, *values):
        self.values = list(values)


class Graph:
    """A graph object ``gorder`` can read.

    ``pointer`` true stores ``n`` in the environment and ignores the
    ``n`` slot. ``pointer`` false rebuilds the count from ``n_slot``,
    ``directed``, and the edge ends, which are 0-based vertex ids.
    """

    def __init__(
        self,
        n=0,
        *,
        classes=("igraph",),
        length=10,
        env=True,
        pointer=True,
        n_slot=None,
        directed=None,
        from_=None,
        to=None,
        atomic=None,
    ):
        if isinstance(classes, str):
            classes = [classes]
        self.classes = list(classes)
        self.length = length
        self.atomic = atomic
        self.n_slot = n_slot
        self.directed = directed
        self.from_ = from_
        self.to = to
        if env is True:
            stored = int(n) if pointer else None
            self.env = Environment(stored)
        elif env is False or env is None:
            self.env = None
        else:
            self.env = env


def _inherits_igraph(graph) -> bool:
    classes = getattr(graph, "classes", None)
    if classes is None:
        return False
    if isinstance(classes, str):
        classes = [classes]
    return "igraph" in list(classes)


def _trunc_int64(value: float) -> int:
    """The installed cast of a double to ``igraph_integer_t``."""

    if (
        math.isnan(value)
        or math.isinf(value)
        or value >= 2**63
        or value < -2**63
    ):
        return _INT64_MIN
    return int(math.trunc(value))


def _real0(slot) -> float:
    if slot is None:
        raise IgraphError(
            "REAL() can only be applied to a 'numeric', not a 'NULL'"
        )
    if isinstance(slot, Int):
        raise IgraphError(
            "REAL() can only be applied to a 'numeric', not a 'integer'"
        )
    if not isinstance(slot, Real):
        raise IgraphError(
            "REAL() can only be applied to a 'numeric', not a 'NULL'"
        )
    return slot.values[0]


def _logical0(slot):
    if slot is None:
        raise IgraphError(
            "LOGICAL() can only be applied to a 'logical', not a 'NULL'"
        )
    if isinstance(slot, Real):
        raise IgraphError(
            "LOGICAL() can only be applied to a 'logical', not a 'double'"
        )
    if isinstance(slot, Int):
        raise IgraphError(
            "LOGICAL() can only be applied to a 'logical', not a 'integer'"
        )
    if not isinstance(slot, Logical):
        raise IgraphError(
            "LOGICAL() can only be applied to a 'logical', not a 'NULL'"
        )
    return slot.values[0]


def _edge_ids(slot) -> list:
    if isinstance(slot, Int):
        return list(slot.values)
    if isinstance(slot, Real):
        ids = []
        for value in slot.values:
            converted = _trunc_int64(value)
            if converted != value:
                raise IgraphError(_EDGE_ASSERTION)
            ids.append(converted)
        return ids
    raise IgraphError(_EDGE_ASSERTION)


def _restore(graph) -> int:
    count = _trunc_int64(_real0(graph.n_slot))
    _logical0(graph.directed)
    sources = _edge_ids(graph.from_ if graph.from_ is not None else Int())
    targets = _edge_ids(graph.to if graph.to is not None else Int())
    if count < 0:
        raise IgraphError(_NEGATIVE_VERTICES)
    for index, source in enumerate(sources):
        target = targets[index]
        if source < 0 or target < 0 or source > count - 1 or target > count - 1:
            raise IgraphError(_OUT_OF_RANGE)
    return count


def _vertex_count(graph) -> int:
    length = getattr(graph, "length", None)
    if length == 10 and getattr(graph, "atomic", None) == "integer":
        raise IgraphError(
            "VECTOR_ELT() can only be applied to a 'list', not a 'integer'"
        )
    env = getattr(graph, "env", None)
    if length != 10 or not isinstance(env, Environment):
        if length == 11:
            raise IgraphError(_OLD_TINY)
        raise IgraphError(_OLD)
    if env.pointer is not None:
        return env.pointer
    count = _restore(graph)
    env.pointer = count
    return count


def gorder(graph=_MISSING):
    """Return the number of vertices in ``graph`` as a length-1 double."""

    if graph is _MISSING:
        raise IgraphError('argument "graph" is missing, with no default')
    if graph is None:
        raise IgraphError("Must provide a graph object (provided `NULL`).")
    if isinstance(graph, MissingArg):
        raise IgraphError("Must provide a graph object (missing argument).")
    if not _inherits_igraph(graph):
        raise IgraphError(
            "Must provide a graph object (provided wrong object type)."
        )
    return float(_vertex_count(graph))
