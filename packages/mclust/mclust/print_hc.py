"""Printer for model-based agglomerative hierarchical clustering results."""

from __future__ import annotations

import textwrap
from typing import Any


def _attribute(x: Any, name: str) -> Any:
    if isinstance(x, dict):
        return x.get(name)
    return getattr(x, name, None)


def _catwrap(value: Any, width: int = 80) -> None:
    text = str(value)
    print("\n".join(textwrap.wrap(text, width=width, break_long_words=True,
                                  break_on_hyphens=True)), end=" \n")


def print_hc(x: Any, **kwargs: Any) -> Any:
    """Print an ``hc`` result and return it unchanged."""
    del kwargs
    call = _attribute(x, "call")
    if call is not None:
        print("Call:", end="\n")
        _catwrap(call)
        print()
    _catwrap("Model-Based Agglomerative Hierarchical Clustering")
    model = _attribute(x, "modelName")
    if model is not None:
        print(f"Model name        = {model}", end=" \n")
    use = _attribute(x, "use")
    if use is not None:
        print(f"Use               = {use}", end=" \n")
    dimensions = _attribute(x, "dimensions")
    if dimensions is not None:
        try:
            n_objects = dimensions[0]
        except (IndexError, TypeError):
            n_objects = dimensions
        print(f"Number of objects = {n_objects}", end=" \n")
    return x


__all__ = ["print_hc"]
