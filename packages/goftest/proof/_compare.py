"""Shared check for the goftest proofs.

Reads the TSV the R script wrote and compares it with the Python values.
This module never calls R. Timing is one untimed call, then the median of 20
timed calls, both on the Python side and on the R side.
"""

from __future__ import annotations

import math
import statistics
import time
from pathlib import Path

TOL = 1e-8
OUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def _parse(raw):
    if raw in ("NA", "NaN"):
        return math.nan
    if raw == "Inf":
        return math.inf
    if raw == "-Inf":
        return -math.inf
    try:
        return float(raw)
    except ValueError:
        return raw


def read_r(name):
    values, times = {}, {}
    for line in (OUT / f"{name}-r.tsv").read_text().splitlines()[1:]:
        kind, case, index, raw = line.split("\t", 3)
        if kind == "time_ms":
            times[case] = float(raw)
        else:
            values.setdefault(case, {})[int(index)] = _parse(raw)
    return values, times["main"]


def _pair(r, p):
    """(matches, absolute difference) for one R value and one Python value."""
    if isinstance(r, str) or isinstance(p, str):
        same = r == p
        return same, 0.0 if same else math.inf
    if math.isnan(r) or math.isnan(p):
        return math.isnan(r) and math.isnan(p), 0.0
    if math.isinf(r) or math.isinf(p):
        same = r == p
        return same, 0.0 if same else math.inf
    d = abs(r - p)
    return d <= TOL, d


def median_ms(call, reps=20):
    call()  # untimed
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        call()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times)


def check(name, py_values, py_call, title):
    """Compare every case, time the Python call, and write the report.

    py_values maps each case to a list of values in R's index order.
    Returns 0 when every value matches within TOL, else 1.
    """
    r_values, r_ms = read_r(name)
    if set(r_values) != set(py_values):
        missing = sorted(set(r_values) ^ set(py_values))
        raise SystemExit(f"case sets differ: {missing[:5]}")

    lines, worst, all_ok, count = [], 0.0, True, 0
    for case in r_values:
        rv = r_values[case]
        pv = py_values[case]
        case_ok, case_worst = len(rv) == len(pv), 0.0
        if case_ok:
            for i in sorted(rv):
                same, d = _pair(rv[i], pv[i - 1])
                count += 1
                case_ok = case_ok and same
                case_worst = max(case_worst, d)
        all_ok = all_ok and case_ok
        worst = max(worst, case_worst)
        lines.append(f"  {case}\tlen={len(rv)}\tmax_abs_diff={case_worst:.3e}\tmatch={'yes' if case_ok else 'no'}")

    py_ms = median_ms(py_call)
    result = "PASS" if all_ok else "FAIL"
    report = [
        f"{title}",
        f"fixed inputs; tolerance {TOL:g}; values compared: {count}; cases: {len(r_values)}",
        "",
        "case comparison (max abs diff per case):",
        *lines,
        "",
        f"max abs diff over all cases: {worst:.3e}",
        f"result: {result} (tolerance {TOL:g})",
        "",
        "timing (median of 20 calls after one untimed call, ms):",
        f"  R       {r_ms:.4f}",
        f"  Python  {py_ms:.4f}",
        f"  speedup (R/Python) {r_ms / py_ms:.2f}",
    ]
    text = "\n".join(report) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}-python.txt").write_text(text)
    print(text, end="")
    return 0 if all_ok else 1
