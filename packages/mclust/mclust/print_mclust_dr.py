"""Summaries and printers for ``MclustDR`` results."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

import numpy as np

__all__ = [
    "summary_MclustDR",
    "summary_MclustDRsubsel",
    "print_MclustDR",
    "print_MclustDRsubsel",
    "print_summary_MclustDR",
]


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _level_key(value: str) -> tuple[int, float, str]:
    try:
        return (0, float(value), value)
    except ValueError:
        return (1, 0.0, value)


def _table(values: list[str]) -> tuple[list[str], np.ndarray]:
    """Return ``(levels, counts)`` like R's ``table()`` on a factor."""
    levels = sorted(set(values), key=_level_key)
    counter = Counter(values)
    return levels, np.asarray([counter[x] for x in levels], dtype=int)


def _observation_labels(obj: Any) -> tuple[list[str], list[str]]:
    """Return ``(levels, labels)``: the factor levels and the class of each observation.

    R stores one label per observation in ``classification``. For an ``Mclust``
    ``MclustDR`` that is the case here too. For ``MclustDA``, ``classification``
    holds only the level names, and the class is then ``class2mixcomp`` of the
    per-observation mixture component in ``mixcomp``.
    """
    raw = [str(x) for x in np.asarray(_get(obj, "classification", [])).reshape(-1)]
    mixcomp = _get(obj, "mixcomp", None)
    if mixcomp is None:
        return sorted(set(raw), key=_level_key), raw
    comp = [str(int(m)) for m in np.asarray(mixcomp).reshape(-1)]
    if len(raw) == len(comp):
        return sorted(set(raw), key=_level_key), raw
    cl2mc = _get(obj, "class2mixcomp", None)
    if cl2mc is None:
        cl2mc = np.arange(1, len(raw) + 1)
    cl2mc = np.asarray(cl2mc).reshape(-1).astype(int)
    labels = [raw[int(cl2mc[int(m) - 1]) - 1] for m in np.asarray(mixcomp).reshape(-1)]
    return raw, labels


def _levels_and_counts(obj: Any) -> tuple[list[str], np.ndarray, Any]:
    """Mirror R: ``n = table(classification)``; ``G`` is ``object$G`` (Mclust)
    or ``table(class2mixcomp)`` (MclustDA)."""
    levels, labels = _observation_labels(obj)
    counter = Counter(labels)
    counts = np.asarray([counter[x] for x in levels], dtype=int)
    if _get(obj, "type") == "Mclust":
        groups: Any = int(_get(obj, "G"))
    else:
        _, groups = _table([str(x) for x in np.asarray(_get(obj, "class2mixcomp")).reshape(-1)])
    return levels, counts, groups


def summary_MclustDR(object: Any, numdir: int | None = None, std: bool = False, **_: Any) -> dict[str, Any]:
    """Return the R ``summary.MclustDR`` list as a Python dictionary."""
    if numdir is None:
        numdir = int(_get(object, "numdir"))
    numdir = int(numdir)
    levels, counts, groups = _levels_and_counts(object)
    basis_name = "std.basis" if std else "basis"
    basis = np.asarray(_get(object, basis_name), dtype=float)[:, :numdir]
    evalues = np.asarray(_get(object, "evalues"), dtype=float)[:numdir]
    cumulative = np.cumsum(evalues) / np.sum(evalues) * 100.0
    return {
        "type": _get(object, "type"),
        "modelName": _get(object, "modelName"),
        "classes": levels,
        "n": counts,
        "G": groups,
        "basis": basis,
        "std": bool(std),
        "std.basis": np.asarray(_get(object, "std.basis"), dtype=float)[:, :numdir],
        "evalues": evalues,
        "evalues.cumperc": cumulative,
    }


def summary_MclustDRsubsel(object: Any, **kwargs: Any) -> dict[str, Any]:
    """Summary method for a subset-selected DR object."""
    obj = dict(object) if isinstance(object, Mapping) else object
    if isinstance(obj, dict):
        obj["basis"] = _get(object, "basisx")
        obj["std.basis"] = _get(object, "std.basisx")
    return summary_MclustDR(obj, **kwargs)


def _sci_parts(value: float, digits: int) -> tuple[int, int]:
    """Return ``(kpower, nsig)`` as R's ``scientific()``: the decimal exponent and
    the significant digits (at most ``digits``) left after rounding."""
    if value == 0:
        return 0, 1
    mantissa, exponent = f"{abs(value):.{digits - 1}e}".split("e")
    return int(exponent), len(mantissa.replace(".", "").rstrip("0")) or 1


def _r_format_column(values: np.ndarray, digits: int) -> list[str]:
    """Format one matrix column the way R's ``formatReal`` does in ``print.default``.

    All entries of the column share one number of decimals, chosen so that each
    entry shows at least ``digits`` significant digits where needed. Values are
    printed from the unrounded number, not from the rounded significant digits.
    """
    finite = [float(v) for v in values if np.isfinite(v)]
    if not finite:
        return [_r_special(v) for v in values]
    parts = [_sci_parts(v, digits) for v in finite]
    negative = [v < 0 for v in finite]
    rgt = max(max(nsig - kp - 1, 0) for kp, nsig in parts)
    left = max((int(neg) + (kp + 1 if kp >= 0 else 1)) for neg, (kp, _) in zip(negative, parts))
    width_fixed = left + (rgt + 1 if rgt > 0 else 0)
    mxsig = max(nsig for _, nsig in parts)
    max_exp = max(abs(kp) for kp, _ in parts)
    width_sci = int(any(negative)) + (mxsig + 1 if mxsig > 1 else mxsig) + (4 if max_exp < 100 else 5)
    out = []
    for v in values:
        if not np.isfinite(v):
            out.append(_r_special(v))
        elif width_fixed <= width_sci:
            out.append(f"{v:.{rgt}f}")
        else:
            out.append(f"{v:.{mxsig - 1}e}")
    return out


def _r_special(value: float) -> str:
    if np.isnan(value):
        return "NaN"
    return "Inf" if value > 0 else "-Inf"


def _matrix_lines(matrix: np.ndarray, row_names: list[str], col_names: list[str], digits: int = 5) -> list[str]:
    """Lines of R's ``print.default`` for a numeric matrix: per-column formatting,
    right-aligned columns, left-aligned row names, no trailing blanks."""
    arr = np.asarray(matrix, dtype=float)
    columns = []
    for j in range(arr.shape[1]):
        cells = _r_format_column(arr[:, j], digits)
        width = max([len(col_names[j])] + [len(cell) for cell in cells])
        columns.append((cells, width))
    row_width = max([len(name) for name in row_names] + [0])
    header = " " * row_width + "".join(" " + col_names[j].rjust(w) for j, (_, w) in enumerate(columns))
    lines = [header]
    for i, name in enumerate(row_names):
        lines.append(name.ljust(row_width) + "".join(" " + cells[i].rjust(w) for cells, w in columns))
    return lines


def _count_table_lines(row_names: list[str], counts: np.ndarray, header: str) -> list[str]:
    """Lines of R's ``print(table, quote = FALSE, right = TRUE)`` for one count column."""
    row_width = max([len(header)] + [len(name) for name in row_names])
    cells = [str(int(n)) for n in counts]
    col_width = max([len("n")] + [len(cell) for cell in cells])
    lines = [" " * row_width, header.ljust(row_width) + " " + "n".rjust(col_width)]
    lines += [name.rjust(row_width) + " " + cell.rjust(col_width) for name, cell in zip(row_names, cells)]
    return lines


def _summary_text(x: Mapping[str, Any], digits: int = 5) -> str:
    title = "Dimension reduction for model-based clustering and classification"
    out = ["-" * min(len(title), 80) + " ", title + " ", "-" * min(len(title), 80) + " ", ""]
    typ = x["type"]
    if typ == "Mclust":
        out += [f"Mixture model type: {typ} ({x['modelName']}, {x['G']}) "]
        out += _count_table_lines([str(c) for c in x["classes"]], x["n"], "Clusters")
    elif typ in ("MclustDA", "EDDA"):
        out += [f"Mixture model type: {typ}", "        ", "Classes  n Model G"]
        out += [f"{cls} {int(n)} {model} {int(g)}" for cls, n, model, g in zip(x["classes"], x["n"], x["modelName"], x["G"])]
    else:
        raise ValueError("invalid model type")
    out += ["", "Standardized basis vectors using predictors scaled to have std.dev. equal to one:"
            if x["std"] else "Estimated basis vectors: "]
    p = x["basis"].shape[0]
    rows = ["Length", "Left", "Right", "Bottom"][:p]
    cols = [f"Dir{i}" for i in range(1, x["basis"].shape[1] + 1)]
    out += _matrix_lines(x["basis"], rows, cols, digits)
    out += [""]
    ev = np.vstack([x["evalues"], x["evalues.cumperc"]])
    out += _matrix_lines(ev, ["Eigenvalues", "Cum. %"], cols, digits)
    return "\n".join(out) + "\n"


def print_summary_MclustDR(x: Mapping[str, Any], digits: int = 5, **_: Any) -> Any:
    """Print a ``summary.MclustDR`` dictionary and return invisibly."""
    print(_summary_text(x, digits), end="")
    return x


def print_MclustDR(x: Any, digits: int = 7, **_: Any) -> Any:
    """Print an ``MclustDR`` object's available components."""
    cls = "MclustDR"
    keys = list(x.keys()) if isinstance(x, Mapping) else list(vars(x))
    keys = [key for key in keys if not str(key).startswith("_")]
    if "type" in keys and "call" not in keys:
        keys.insert(0, "call")
    if "basisx" in keys and "std.basisx" in keys:
        pass
    print(f"'{cls}' model object: \n")
    print("Available components: ")
    for i in range(0, len(keys), 4):
        chunk = keys[i : i + 4]
        fields = [f'"{key}"'.ljust(17 if j < len(chunk) - 1 else 16) for j, key in enumerate(chunk)]
        print(f"[{i + 1}]".rjust(4) + " " + "".join(fields))
    return x


def print_MclustDRsubsel(x: Any, digits: int = 7, **kwargs: Any) -> Any:
    """Print a subset-selected DR object using the MclustDR printer."""
    return print_MclustDR(x, digits=digits, **kwargs)

