"""Shared fixtures, record format, and comparator for the BIC proofs.

The R side writes ``docs/output/<name>-r.txt`` (see ``bic_proof_common.R``).
The Python side builds the same records from the same fixtures, compares
them token by token (numbers within 1e-8, strings exactly), and writes
``docs/output/<name>-py.txt``.
"""

from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
TOL = 1e-8

MODELS14 = ["EII", "VII", "EEI", "VEI", "EVI", "VVI", "EEE",
            "VEE", "EVE", "VVE", "EEV", "VEV", "EVV", "VVV"]


def fixture(gvals, jidx):
    """Same grid as ``fixture`` in bic_proof_common.R."""
    I = np.asarray(gvals, dtype=float)[:, None]
    J = np.asarray(jidx, dtype=float)[None, :]
    m = -1000.0 - (I * 0.5 + np.mod(I * J, 5) * 2.5 + J * 0.25)
    m = np.asarray(m, dtype=float)
    m[np.mod(I + J, 7) == 0] = np.nan
    return m


def bic_obj(gvals, jidx, models, n, d, tag, cls="mclustBIC", noise=False):
    """Dict form of a mclustBIC object (values matrix plus attributes)."""
    values = fixture(gvals, jidx)
    obj: dict[str, Any] = {
        "values": values,
        "G": list(gvals),
        "modelNames": list(models),
        "n": n,
        "d": d,
        "tag": tag,
        "class": cls,
        "criterion": "BIC",
        "returnCodes": np.zeros(values.shape, dtype=int),
    }
    if noise:
        obj["noise"] = True
    return obj


def fmt(x: Any) -> str:
    x = float(x)
    if math.isnan(x):
        return "NA"
    return "%.17g" % x


def tok(a: Any) -> str:
    if a is None:
        return "NULL"
    if isinstance(a, (list, tuple)):
        return ",".join(str(v) for v in a)
    if isinstance(a, (int, float, np.number)) and not isinstance(a, bool):
        return fmt(a)
    return str(a)


def line(key: str, vals) -> str:
    return "\t".join([key, *vals])


def record_matrix(case_id: str, x: dict | None) -> list[str]:
    out = [f"case\t{case_id}"]
    if x is None:
        return out + ["null\t1"]
    v = np.asarray(x["values"], dtype=float)
    out.append(line("dim", [fmt(v.shape[0]), fmt(v.shape[1])]))
    out.append(line("G", [fmt(g) for g in x["G"]]))
    out.append(line("modelNames", [str(m) for m in x["modelNames"]]))
    out.append(line("n", [tok(x.get("n"))]))
    out.append(line("d", [tok(x.get("d"))]))
    out.append(line("tag", [tok(x.get("tag"))]))
    out.append(line("criterion", [tok(x.get("criterion"))]))
    out.append(line("class", [tok(x.get("class"))]))
    for row in v:
        out.append(line("row", [fmt(val) for val in row]))
    return out


def record_pick(case_id: str, res: dict | None) -> list[str]:
    out = [f"case\t{case_id}"]
    if res is None:
        return out + ["null\t1"]
    out.append(line("values", [fmt(val) for val in res["values"]]))
    names = res.get("names")
    out.append(line("names", ["NULL"] if names is None else list(names)))
    return out


def record_value(case_id: str, value: float) -> list[str]:
    return [f"case\t{case_id}", line("value", [fmt(value)])]


def timed_median_ms(fn: Callable[[], Any], reps: int = 20) -> float:
    """Median of ``reps`` timed calls, in milliseconds (perf_counter)."""
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times)


def _num(tok_: str):
    try:
        return float(tok_)
    except ValueError:
        return None


def compare(ref: list[str], got: list[str]) -> tuple[bool, float]:
    """Return (matches, max_abs_diff) over the record tokens.

    Numbers are compared with NA == NA; strings must be equal. ``time_ms``
    lines are not compared.
    """
    ref = [r for r in ref if not r.startswith("time_ms\t")]
    got = [g for g in got if not g.startswith("time_ms\t")]
    if len(ref) != len(got):
        return False, math.inf
    ok = True
    max_diff = 0.0
    for a, b in zip(ref, got):
        ta, tb = a.split("\t"), b.split("\t")
        if len(ta) != len(tb) or ta[0] != tb[0]:
            ok = False
            continue
        for x, y in zip(ta[1:], tb[1:]):
            fx, fy = _num(x), _num(y)
            if fx is None or fy is None:
                if x != y:
                    ok = False
                continue
            if math.isnan(fx) or math.isnan(fy):
                if math.isnan(fx) != math.isnan(fy):
                    ok = False
                    max_diff = math.inf
                continue
            max_diff = max(max_diff, abs(fx - fy))
    if max_diff > TOL:
        ok = False
    return ok, max_diff


def read_r_record(name: str) -> tuple[list[str], float]:
    lines = (OUT / f"{name}-r.txt").read_text().splitlines()
    r_ms = float("nan")
    for ln in lines:
        if ln.startswith("time_ms\t"):
            r_ms = float(ln.split("\t")[1])
    return lines, r_ms


def report(name: str, py_lines: list[str], py_ms: float) -> None:
    r_lines, r_ms = read_r_record(name)
    matches, max_diff = compare(r_lines, py_lines)
    speedup = r_ms / py_ms if py_ms > 0 else math.nan
    summary = [
        f"# {name}",
        f"# matches\t{'yes' if matches else 'no'}",
        f"# max_abs_diff\t{max_diff:.3g}",
        f"# R_ms\t{r_ms:.4f}",
        f"# Python_ms\t{py_ms:.4f}",
        f"# speedup\t{speedup:.3g}",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}-py.txt").write_text(
        "\n".join(summary + py_lines + [f"time_ms\t{py_ms:.17g}"]) + "\n"
    )
    print("\n".join(summary))
