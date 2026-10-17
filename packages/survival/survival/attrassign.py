"""Map R-style model-matrix assign vectors to S-Plus-style lists."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


def _is_terms(tt: Any) -> bool:
    if isinstance(tt, dict):
        return tt.get("class") == "terms" or "term_labels" in tt
    klass = getattr(tt, "class_", None)
    if klass == "terms":
        return True
    if isinstance(getattr(tt, "__class__", None), type) and tt.__class__.__name__ == "terms":
        return True
    return hasattr(tt, "term_labels") and getattr(tt, "is_terms", False)


def _term_labels(tt: Any) -> list[str]:
    if isinstance(tt, dict):
        return list(tt["term_labels"])
    labels = getattr(tt, "term_labels", None)
    if labels is None:
        labels = getattr(tt, "term.labels", None)
    return list(labels)


def _matrix_assign(object: Any):
    assign = getattr(object, "assign", None)
    if assign is None and isinstance(object, dict):
        assign = object.get("assign")
    return assign


def attrassign(object: Any, tt: Any) -> OrderedDict[str, list[int]]:
    """Create S-Plus-style assign lists from an R-style assign vector."""
    if not _is_terms(tt):
        raise ValueError("need terms object")
    aa = _matrix_assign(object)
    if aa is None:
        raise ValueError("argument is not really a model matrix")
    ll = _term_labels(tt)
    names = ["(Intercept)", *ll]
    assign = [int(value) for value in aa]
    temp = [names[value] for value in assign]
    unique_temp = list(dict.fromkeys(temp))
    out: OrderedDict[str, list[int]] = OrderedDict()
    for level in unique_temp:
        out[level] = [index + 1 for index, name in enumerate(temp) if name == level]
    return out
