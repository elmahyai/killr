"""Whether an igraph graph is directed.

``is_directed`` checks the argument with ``ensure_igraph`` and then reads
``igraph_is_directed``. That flag is the ``directed`` field of the
external pointer. The R build stores it as an ``int``, so a logical
``NA`` stays missing instead of becoming true. The result is a length-1
logical.

A current graph is a list of length 10 whose last element is an
environment. A live pointer keeps the flag that was stored with it, so
a rewritten directed slot does not change the result. When the pointer
is missing, ``warn_version`` rebuilds it: the numeric ``n`` slot is
truncated toward zero to a 64-bit integer, ``LOGICAL()`` reads the first
directed value, and the edge ends are checked. Only then is that
directed value kept.
"""

from __future__ import annotations

import math


_MISSING = object()
_UNSET = object()
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
    """An ``is_directed`` failure, using R's condition message."""


class NALogical:
    """R's logical missing value, the ``NA_LOGICAL`` integer."""


NA = NALogical()


class MissingArg:
    """The value produced by ``rlang::missing_arg()``."""


def missing_arg():
    """Return the object ``rlang::missing_arg()`` produces."""

    return MissingArg()


class Environment:
    """The graph environment.

    ``live`` means the external pointer is set. ``directed`` is the
    integer flag stored in that pointer, which may be ``NA``.
    """

    def __init__(self, live=False, directed=None):
        self.live = live
        self.directed = directed


class Real:
    """An R numeric vector."""

    def __init__(self, *values):
        self.values = [float(value) for value in values]


class Int:
    """An R integer vector."""

    def __init__(self, *values):
        self.values = [int(value) for value in values]


class Logical:
    """An R logical vector. Values are ``True``, ``False``, or ``NA``."""

    def __init__(self, *values):
        self.values = list(values)


class Character:
    """An R character vector."""

    def __init__(self, *values):
        self.values = [str(value) for value in values]


class Complex:
    """An R complex vector."""

    def __init__(self, *values):
        self.values = list(values)


class Raw:
    """An R raw vector."""

    def __init__(self, *values):
        self.values = list(values)


class ListVec:
    """An R list."""

    def __init__(self, *values):
        self.values = list(values)


class Graph:
    """A graph object ``is_directed`` can read.

    ``pointer`` true stores ``directed`` on the external pointer and
    ignores the directed slot. ``pointer`` false rebuilds the flag from
    ``n_slot``, the directed slot, and the edge ends, which are 0-based
    vertex ids. ``directed`` on that path is the slot, and the first
    element is the one ``LOGICAL()`` reads.
    """

    def __init__(
        self,
        n=0,
        directed=False,
        *,
        classes=("igraph",),
        length=10,
        env=True,
        pointer=True,
        n_slot=_UNSET,
        directed_slot=_UNSET,
        from_=_UNSET,
        to=_UNSET,
        atomic=None,
    ):
        if isinstance(classes, str):
            classes = [classes]
        self.classes = list(classes)
        self.length = length
        self.atomic = atomic
        self.n_slot = Real(float(n)) if n_slot is _UNSET else n_slot
        self.from_ = Int() if from_ is _UNSET else from_
        self.to = Int() if to is _UNSET else to
        if env is True and pointer:
            if directed is not True and directed is not False and directed is not NA:
                raise TypeError("a live directed flag is TRUE, FALSE, or NA")
            self.env = Environment(True, directed)
            self.directed = (
                Logical(directed) if directed_slot is _UNSET else directed_slot
            )
        else:
            self.directed = (
                _as_directed_slot(directed)
                if directed_slot is _UNSET
                else directed_slot
            )
            if env is True:
                self.env = Environment(False, None)
            elif env is False or env is None:
                self.env = None
            else:
                self.env = env


def _as_directed_slot(directed):
    if isinstance(directed, (Logical, Real, Int, Character, Complex, Raw, ListVec)):
        return directed
    if directed is None:
        return None
    if isinstance(directed, (list, tuple)):
        return Logical(*directed)
    return Logical(directed)


def _inherits_igraph(graph) -> bool:
    classes = getattr(graph, "classes", None)
    if classes is None:
        return False
    if isinstance(classes, str):
        classes = [classes]
    return "igraph" in list(classes)


def _type_name(slot) -> str:
    if slot is None:
        return "NULL"
    if isinstance(slot, Real):
        return "double"
    if isinstance(slot, Int):
        return "integer"
    if isinstance(slot, Logical):
        return "logical"
    if isinstance(slot, Character) or isinstance(slot, str):
        return "character"
    if isinstance(slot, Complex):
        return "complex"
    if isinstance(slot, Raw):
        return "raw"
    if isinstance(slot, ListVec):
        return "list"
    return "NULL"


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
    name = _type_name(slot)
    if name != "double":
        raise IgraphError(
            f"REAL() can only be applied to a 'numeric', not a '{name}'"
        )
    return slot.values[0]


def _logical0(slot):
    name = _type_name(slot)
    if name != "logical":
        raise IgraphError(
            f"LOGICAL() can only be applied to a 'logical', not a '{name}'"
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


def _restore(graph):
    """Rebuild the pointer and return the directed integer that was stored."""

    count = _trunc_int64(_real0(graph.n_slot))
    flag = _logical0(graph.directed)
    sources = _edge_ids(graph.from_)
    targets = _edge_ids(graph.to)
    if count < 0:
        raise IgraphError(_NEGATIVE_VERTICES)
    for index, source in enumerate(sources):
        if index >= len(targets):
            raise IgraphError(_EDGE_ASSERTION)
        target = targets[index]
        if source < 0 or target < 0 or source > count - 1 or target > count - 1:
            raise IgraphError(_OUT_OF_RANGE)
    return flag


def _pointer_directed(graph):
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
    if env.live:
        return env.directed
    flag = _restore(graph)
    env.live = True
    env.directed = flag
    return flag


def is_directed(graph=_MISSING):
    """Return whether ``graph`` is directed, as a length-1 logical.

    ``True`` and ``False`` are the usual flags. ``NA`` is R's logical
    missing value, kept when the restored slot is missing.
    """

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
    return _pointer_directed(graph)
