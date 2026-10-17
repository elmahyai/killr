"""Summary and printing methods for ``MclustSSC`` results."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

import numpy as np

__all__ = [
    "summary_MclustSSC",
    "print_MclustSSC",
    "print_summary_MclustSSC",
]


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _r_num(value: Any, digits: int = 7) -> str:
    return f"{float(value):.{digits}g}"


def _is_missing(value: Any) -> bool:
    return value is None or (
        isinstance(value, (float, np.floating)) and np.isnan(value)
    )


def _ordered(values: Any) -> list[str]:
    unique = list(dict.fromkeys(str(x) for x in values if not _is_missing(x)))
    try:
        return sorted(unique, key=lambda x: (0, float(x)))
    except ValueError:
        return sorted(unique)


def summary_MclustSSC(
    object_: Any, parameters: bool = False, **_: Any
) -> dict[str, Any]:
    """Return the R ``summary.MclustSSC`` representation."""
    classes = np.asarray(_get(object_, "class", []), dtype=object)
    classification = np.asarray(_get(object_, "classification", []), dtype=object)
    class_levels = _ordered(_get(object_, "classes", []))
    if not class_levels:
        class_levels = _ordered(classes)
    g = int(_get(object_, "G", len(class_levels)))
    nclass = len(class_levels)
    counts = [int(np.sum(classes == level)) for level in class_levels]
    na_count = int(sum(_is_missing(x) for x in classes))
    names = class_levels + (["<NA>"] if na_count else [])
    n = counts + ([na_count] if na_count else [])
    known = np.array(
        [not (x is None or (isinstance(x, float) and np.isnan(x))) for x in classes]
    )
    pred_levels = _ordered(classification)
    table = np.zeros((len(names), len(pred_levels)), dtype=int)
    for i, name in enumerate(names):
        row_mask = ~known if name == "<NA>" else np.array(
            [not _is_missing(x) and str(x) == name for x in classes]
        )
        for j, pred in enumerate(pred_levels):
            table[i, j] = int(np.sum(row_mask & (classification.astype(str) == pred)))
    pars = _get(object_, "parameters", {}) or {}
    pro = _get(pars, "pro", None)
    if pro is None:
        pro = 1.0
    pro = np.asarray(pro, dtype=float)
    mean = np.asarray(_get(pars, "mean", None), dtype=float)
    variance = _get(pars, "variance", {}) or {}
    sigma = _get(variance, "sigma", _get(variance, "sigmasq", None))
    if sigma is not None:
        sigma = np.asarray(sigma, dtype=float)
    return {
        "n": np.asarray(n, dtype=int),
        "d": int(_get(object_, "d", 1)),
        "loglik": _get(object_, "loglik"),
        "df": _get(object_, "df"),
        "bic": _get(object_, "bic"),
        "nclass": nclass,
        "classes": class_levels,
        "G": g,
        "modelName": _get(object_, "modelName"),
        "pro": pro,
        "mean": mean,
        "variance": sigma,
        "noise": False,
        "prior": _get(object_, "prior"),
        "tab": table,
        "tab_names": (names, pred_levels),
        "err": 0.0,
        "printParameters": bool(parameters),
    }


def _r_print_names(names: list[str]) -> str:
    lines = ["Available components: "]
    for start in range(0, len(names), 4):
        chunk = names[start : start + 4]
        quoted = [f'"{x}"' for x in chunk]
        body = "".join(f"{item:<17}" for item in quoted[:-1]) + f"{quoted[-1]:<16}"
        index = start + 1
        lines.append(f"{' ' if index < 10 else ''}[{index}] {body}")
    return "\n".join(lines)


def print_MclustSSC(x: Any, **_: Any) -> Any:
    """Print an ``MclustSSC`` model object and return it."""
    names = list(x.keys()) if isinstance(x, Mapping) else list(vars(x))
    print(f"'MclustSSC' model object:")
    print()
    print(_r_print_names(names))
    return x


def _print_class_table(summary: Mapping[str, Any]) -> list[str]:
    names, preds = summary["tab_names"]
    table = np.asarray(summary["tab"])
    lines = ["       Predicted", "Classes" + "".join(str(x).rjust(3) for x in preds)]
    for name, row in zip(names, table):
        first = str(int(row[0]))
        gap = " " * (5 if len(str(name)) < 4 else 1)
        rest = "".join(
            ("  " if len(str(int(v))) == 1 else " ") + str(int(v))
            for v in row[1:]
        )
        lines.append("   " + str(name) + gap + first + rest)
    return lines


def print_summary_MclustSSC(
    x: Mapping[str, Any], digits: int = 7, **_: Any
) -> Any:
    """Print a ``summary.MclustSSC`` object and return it."""
    title = "Gaussian finite mixture model for semi-supervised classification"
    line = "-" * min(len(title), 80)
    print(line + " ")
    print(title + " ")
    print(line + " ")
    print()
    print(" log-likelihood   n df       BIC")
    print(
        f"{_r_num(x['loglik'], digits):>15} {int(np.sum(x['n'])):3d}"
        f" {_r_num(x['df'], digits):>2} {_r_num(x['bic'], digits):>9}"
    )
    print("       ")
    total = int(np.sum(x["n"]))
    names = list(x["tab_names"][0])
    model = [str(x["modelName"])] * int(x["G"]) + [""]
    gcol = ["1"] * int(x["G"]) + [""]
    print("Classes   n    % Model G")
    for name, count, model_name, g_name in zip(names, x["n"], model, gcol):
        pct = f"{float(count) / total * 100:.2f}".rstrip("0").rstrip(".")
        if "." not in pct:
            pct += ".0"
        print(
            "   "
            + f"{str(name):<5}{int(count):3d}{pct:>5s}{model_name:>6}"
            + ("  " if not g_name else f" {g_name}")
        )
    if x.get("prior") is not None:
        print()
        print(f"Prior: {x['prior']}")
    print()
    print("Classification summary")
    print("-" * min(48, 80) + " ")
    for row in _print_class_table(x):
        print(row)
    return x
