"""Printer for ``summary.MclustDA`` results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _number(value: Any) -> str:
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        return f"{float(value):g}"
    return str(value)


def _table(summary: Mapping[str, Any], key: str) -> list[str]:
    tab = _get(summary, key)
    if tab is None:
        return []
    values = np.asarray(_get(tab, "values", tab))
    dimnames = _get(tab, "dimnames", {}) or {}
    classes = list(_get(dimnames, "Classes", []))
    predicted = list(_get(dimnames, "Predicted", []))
    lines = ["       Predicted", "Classes" + (" " if predicted else "")]
    lines[1] += " ".join(map(str, predicted))
    for name, row in zip(classes, values):
        lines.append(f"{str(name):>7}" + "".join(f" {int(item)}" for item in row))
    return lines


def print_summary_MclustDA(x: Mapping[str, Any], digits: int = 7, **_: Any) -> Any:
    """Print a ``summary.MclustDA`` object and return it unchanged."""
    title = "Gaussian finite mixture model for classification"
    line = "-" * min(len(title), 80)
    print(line, end=" \n")
    print(title, end=" \n")
    print(line, end=" \n\n")
    print(str(_get(x, "type", "")), end=" \n")
    print(line, end=" \n")
    print(" log-likelihood n df  BIC")
    n = np.asarray(_get(x, "n", []))
    print(
        f"{_number(_get(x, 'loglik')):>15} {int(np.sum(n)):d}"
        f" {_number(_get(x, 'df')):>2} {_number(_get(x, 'bic')):>4}"
    )
    print("       ")
    print("Classes n  % Model G")
    classes = list(_get(x, "classes", []))
    models = list(_get(x, "modelName", []))
    groups = list(_get(x, "G", []))
    total = float(np.sum(n))
    for name, count, model, group in zip(classes, n, models, groups):
        pct = f"{float(count) / total * 100:.2f}".rstrip("0").rstrip(".")
        print(f"{str(name):>7} {int(count)} {pct:>2}   {model} {int(group)}")
    print()
    print("Training confusion matrix")
    print(line, end=" \n")
    for row in _table(x, "tab"):
        print(row)
    print()
    print(f"Classification error = {float(_get(x, 'ce')):.4f} ", end="\n")
    print(f"Brier score          = {float(_get(x, 'brier')):.4f} ", end="\n")
    if _get(x, "tab.newdata") is not None:
        print("\nTest confusion matrix")
        print(line, end=" \n")
        for row in _table(x, "tab.newdata"):
            print(row)
        if _get(x, "ce.newdata") is not None:
            print()
            print(f"Classification error = {float(_get(x, 'ce.newdata')):.4f} ", end="\n")
            print(f"Brier score          = {float(_get(x, 'brier.newdata')):.4f} ", end="\n")
    return x


__all__ = ["print_summary_MclustDA"]
