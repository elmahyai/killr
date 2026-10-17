"""Compare the Python drawing log with the log R writes through plot_trace.R.

Each line is tab-separated: a tag, then the fields. A numeric field holds
space-separated numbers printed with ``%.17g`` (``NA`` for missing). A string
field holds space-separated names or codes, and must match exactly. The
comparison reports the largest absolute difference over all numbers.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

PROOF = Path(__file__).resolve().parent


def _num(v: Any) -> str:
    f = float(v)
    if math.isnan(f):
        return "NA"
    return "%.17g" % f


def _nums(arr: Any) -> str:
    a = np.asarray(arr, dtype=float).ravel()
    return " ".join(_num(v) for v in a)


def _strs(values: Iterable[Any]) -> str:
    out = []
    for v in values:
        if isinstance(v, (np.integer,)):
            out.append(str(int(v)))
        elif isinstance(v, (float, np.floating)):
            out.append(_num(v) if not float(v).is_integer() else str(int(v)))
        else:
            out.append(str(v))
    return " ".join(out)


def format_log(log: list[tuple[str, list[Any]]]) -> list[str]:
    """Render a ``Canvas.log`` the way plot_trace.R writes its log."""
    lines: list[str] = []
    for tag, fields in log:
        if tag == "W":
            usr = np.asarray(fields[0], dtype=float)
            lines.append("\t".join(["W", _nums(usr)]))
        elif tag == "P":
            xs, ys, typ, pch, col = fields
            lines.append("\t".join([
                "P", _nums(xs), _nums(ys), _strs(typ), _strs(pch), _strs(col)]))
        elif tag == "I":
            xs, ys, zf, pal, brk = fields
            lines.append("\t".join([
                "I", _nums(xs), _nums(ys), _nums(zf), _strs(pal),
                _nums(brk) if len(brk) else ""]))
        elif tag == "C":
            xs, ys, zf, lv = fields
            lines.append("\t".join(["C", _nums(xs), _nums(ys), _nums(zf), _nums(lv)]))
        elif tag == "H":
            br, dens = fields
            lines.append("\t".join(["H", _nums(br), _nums(dens)]))
        elif tag == "B":
            lines.append("\t".join(["B", _nums(fields[0])]))
        elif tag == "S":
            lines.append("\t".join(["S", _nums(fields[0])]))
        elif tag == "V":
            name, arr = fields
            lines.append("\t".join(["V", name[0], _nums(arr)]))
        elif tag == "U":
            usr, panel = fields
            lines.append("\t".join(["U", _nums(usr), _nums(panel)]))
        else:
            raise ValueError(f"unknown log tag {tag}")
    return lines


def _as_float(tok: str) -> float | None:
    if tok in ("NA", "nan", "NaN"):
        return math.nan
    try:
        return float(tok)
    except ValueError:
        return None


def compare_logs(r_lines: list[str], py_lines: list[str], tol: float = 1e-8) -> dict[str, Any]:
    """Return match flag, max absolute difference, and the first mismatch, if any."""
    result: dict[str, Any] = {"matches": True, "max_abs_diff": 0.0, "first_mismatch": None,
                              "n_r": len(r_lines), "n_py": len(py_lines)}
    if len(r_lines) != len(py_lines):
        result["matches"] = False
        result["first_mismatch"] = f"entry count R={len(r_lines)} Python={len(py_lines)}"
        result["max_abs_diff"] = math.inf
        return result
    max_diff = 0.0
    for idx, (rl, pl) in enumerate(zip(r_lines, py_lines)):
        rf, pf = rl.split("\t"), pl.split("\t")
        if len(rf) != len(pf) or rf[0] != pf[0]:
            result["matches"] = False
            result["first_mismatch"] = f"entry {idx}: tag or field count differs"
            result["max_abs_diff"] = math.inf
            return result
        for k, (rfield, pfield) in enumerate(zip(rf[1:], pf[1:]), start=1):
            rt, pt = rfield.split(" "), pfield.split(" ")
            rt = [t for t in rt if t != ""]
            pt = [t for t in pt if t != ""]
            if len(rt) != len(pt):
                result["matches"] = False
                result["first_mismatch"] = f"entry {idx} ({rf[0]}) field {k}: length {len(rt)} vs {len(pt)}"
                result["max_abs_diff"] = math.inf
                return result
            for a, b in zip(rt, pt):
                fa, fb = _as_float(a), _as_float(b)
                if fa is None or fb is None:
                    if a != b:
                        result["matches"] = False
                        result["first_mismatch"] = f"entry {idx} ({rf[0]}) field {k}: '{a}' vs '{b}'"
                        result["max_abs_diff"] = math.inf
                        return result
                    continue
                if math.isnan(fa) or math.isnan(fb):
                    if not (math.isnan(fa) and math.isnan(fb)):
                        result["matches"] = False
                        result["first_mismatch"] = f"entry {idx} ({rf[0]}) field {k}: NA vs number"
                        result["max_abs_diff"] = math.inf
                        return result
                    continue
                max_diff = max(max_diff, abs(fa - fb))
    result["max_abs_diff"] = max_diff
    result["matches"] = max_diff <= tol
    return result


def read_r_log(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line != ""]
