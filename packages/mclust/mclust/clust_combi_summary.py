"""Summary and printing methods for ``clustCombi`` results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

__all__ = [
    "summary_clust_combi",
    "print_clust_combi",
    "print_summary_clust_combi",
    "summary_clustCombi",
    "print_clustCombi",
    "print_summary_clustCombi",
]


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def summary_clust_combi(object_: Any, **_: Any) -> dict[str, Any]:
    """Build the compact summary returned by ``summary.clustCombi``."""
    output = _get(object_, "MclustOutput", {})
    matrices = _get(object_, "combiM", {})
    g = int(_get(output, "G", _get(object_, "MclustG", 0)))
    model_name = _get(output, "modelName", None)
    if isinstance(matrices, Mapping):
        combi_m = [matrices[k] for k in sorted(matrices)]
    else:
        combi_m = list(matrices)
    return {
        "title": "Combining Gaussian mixture components for clustering",
        "MclustModelName": model_name,
        "MclustG": g,
        "combiM": combi_m,
    }


def _keys(object_: Any) -> list[str]:
    if isinstance(object_, Mapping):
        return list(object_.keys())
    return list(vars(object_))


def print_clust_combi(object_: Any, **_: Any) -> Any:
    """Print a ``clustCombi`` object and return it."""
    output = _get(object_, "MclustOutput", {})
    g = int(_get(output, "G", 0))
    model = _get(output, "modelName", "")
    keys = " ".join(_keys(object_))
    print("'clustCombi' object:")
    print(f" Mclust model: ({model},{g})")
    print(f" Available object components: {keys} ")
    print(" Combining matrix (K+1 classes -> K classes): <object_name>$combiM[[K]]")
    print(" Classification for K classes: <object_name>$classification[[K]]")
    return object_


def _combining_steps(summary: Mapping[str, Any]) -> list[str]:
    matrices = summary["combiM"]
    g = int(summary["MclustG"])
    current = np.arange(1, g + 1)
    lines = [
        "  Step | Classes combined at this step | Class labels after this step",
        "-------|-------------------------------|-----------------------------",
        f"   0   |              ---              | {' '.join(map(str, current))} ",
    ]
    for step in range(1, g):
        matrix = np.asarray(matrices[g - step - 1], dtype=float)
        pairs = np.flatnonzero(np.sum(matrix, axis=1) == 2)
        row = int(pairs[0])
        columns = np.flatnonzero(matrix[row] != 0)
        combined = current[columns]
        next_current = current[np.argmax(matrix, axis=1)]
        lines.append(
            f"   {step}   | {combined[0]:>13} & {combined[1]:<13} | "
            f"{' '.join(map(str, next_current))} "
        )
        current = next_current
    return lines


def print_summary_clust_combi(summary: Mapping[str, Any], **_: Any) -> Any:
    """Print a ``summary.clustCombi`` dictionary and return it."""
    title = str(summary.get("title", ""))
    model = summary.get("MclustModelName")
    g = int(summary.get("MclustG", 0))
    print("-" * len(title))
    print(f"{title} ")
    print("-" * len(title))
    print()
    print(f"Mclust model name: {'' if model is None else model} ")
    print(f"Number of components: {g} ")
    print()
    print("Combining steps:")
    print()
    for line in _combining_steps(summary):
        print(line)
    return summary


summary_clustCombi = summary_clust_combi
print_clustCombi = print_clust_combi
print_summary_clustCombi = print_summary_clust_combi
