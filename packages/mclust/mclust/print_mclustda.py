"""Printer for discriminant-analysis MclustDA model objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _component_names(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return [str(name) for name in value]
    return [str(name) for name in vars(value)]


def _names_text(names: list[str]) -> str:
    """Format names like R's print.default (four or more columns)."""
    if not names:
        return ""
    quoted = [f'"{name}"' for name in names]
    # R selects eight columns for this compact output at the usual widths.
    width = max(9, max(map(len, quoted)) + 1)
    lines: list[str] = []
    for start in range(0, len(quoted), 8):
        chunk = quoted[start : start + 8]
        body = "".join(
            item.ljust(width if i < len(chunk) - 1 else width - 1)
            for i, item in enumerate(chunk)
        )
        index = start + 1
        prefix = " " if len(names) > 8 and index < 10 else ""
        lines.append(f"{prefix}[{index}] {body}")
    return "\n".join(lines)


def _class_table(models: Any) -> str:
    if isinstance(models, Mapping):
        items = list(models.items())
    else:
        items = list(enumerate(models, 1))
    rows = []
    for label, model in items:
        rows.append(
            (
                str(label),
                str(_get(model, "n", "")),
                str(_get(model, "modelName", "")),
                str(_get(model, "G", "")),
            )
        )
    if not rows:
        return "Classes       n Model G"
    name_width = max(10, max(len(row[0]) for row in rows))
    n_width = max(2, max(len(row[1]) for row in rows))
    model_width = max(3, max(len(row[2]) for row in rows))
    header = (
        "Classes"
        + " " * (name_width - len("Classes") + 4)
        + "n"
        + " "
        + "Model"
        + " " * max(1, model_width - len("Model") + 1)
        + "G"
    )
    lines = [header]
    for label, n, model, groups in rows:
        lines.append(
            "  "
            + label.ljust(name_width)
            + " "
            + n.rjust(n_width)
            + "   "
            + model.ljust(model_width)
            + " "
            + groups
        )
    return "\n".join(lines)


def print_MclustDA(x: Any, **_: Any) -> Any:
    """Print an ``MclustDA`` model object and return it unchanged."""
    models = _get(x, "models", {})
    print("'MclustDA' model object:")
    print(" " * 12)
    print(_class_table(models))
    print()
    print("Available components: ")
    names = _component_names(x)
    if names:
        print(_names_text(names))
    return x


__all__ = ["print_MclustDA"]
