"""Proof: mass.datasets loads every MASS data set as R does.

Compares each data set's columns, values, factor levels, row names and time-series
attributes with R's reference (docs/output/datasets-r.json, written by
proof/export-datasets-r.R). Numbers must agree within 1e-8 (NA matches NA). Text,
levels and row names must agree exactly. Times the Python loader (one untimed call,
then the median of 20 timed calls) against R's data() loads.

Run from packages/MASS:  .venv/bin/python proof/datasets-py.py
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
# mass/__init__ imports the repo's Formula package (packages/Formula).
sys.path.insert(0, str(ROOT.parent / "Formula"))

from mass import datasets as ds  # noqa: E402

TOL = 1e-8
REF = json.loads((ROOT / "docs" / "output" / "datasets-r.json").read_text(encoding="utf-8"))["datasets"]
OUT = ROOT / "docs" / "output"


def _num(text):
    if text is None or text == "NA":
        return math.nan
    return float(text)


def _compare_column(py_col, ref_col, kind):
    """Return (ok, max_abs_diff, reason) for one column."""
    if len(py_col) != len(ref_col):
        return False, math.inf, f"length {len(py_col)} vs {len(ref_col)}"
    max_diff = 0.0
    for a, b in zip(py_col, ref_col):
        if kind in ("numeric", "integer"):
            r = _num(b)
            if math.isnan(a) and math.isnan(r):
                continue
            if math.isnan(a) != math.isnan(r):
                return False, math.inf, f"NA pattern {a!r} vs {b!r}"
            max_diff = max(max_diff, abs(a - r))
        elif kind == "logical":
            expected = None if b is None or b == "NA" else (b == "TRUE")
            if a != expected:
                return False, math.inf, f"logical {a!r} vs {b!r}"
        else:
            expected = None if b is None or b == "NA" else b
            if a != expected:
                return False, math.inf, f"text {a!r} vs {b!r}"
    return max_diff <= TOL, max_diff, "" if max_diff <= TOL else f"max_abs_diff {max_diff}"


def _check(name, entry):
    """Return (ok, max_abs_diff, n_values, reasons)."""
    meta = ds._meta(name)
    types = {c["name"]: c["type"] for c in meta["columns"]}
    value = ds.load(name)
    reasons = []
    max_diff = 0.0
    n_values = 0
    kind = entry["kind"]
    ref_values = entry["values"]

    if kind == "data.frame":
        py_cols = value
        if list(py_cols) != entry["columns"]:
            reasons.append(f"columns {list(py_cols)} vs {entry['columns']}")
    elif kind == "ts":
        py_cols = {"value": value["values"]}
        start, end, freq = value["tsp"]
        r_start, r_end, r_freq = (float(v) for v in entry["tsp"])
        if max(abs(start - r_start), abs(end - r_end), abs(freq - r_freq)) > TOL:
            reasons.append(f"tsp {value['tsp']} vs {entry['tsp']}")
    elif kind == "numeric":
        py_cols = {"value": value}
    elif kind == "list":
        py_cols = value
        if list(py_cols) != entry["columns"]:
            reasons.append(f"list names {list(py_cols)} vs {entry['columns']}")
    else:
        reasons.append(f"unknown kind {kind}")
        return False, math.inf, 0, reasons

    for col in entry["columns"]:
        if col not in py_cols:
            reasons.append(f"missing column {col}")
            continue
        col_type = types.get(col, "numeric")
        ok, d, why = _compare_column(py_cols[col], ref_values[col], col_type)
        n_values += len(py_cols[col])
        if d != math.inf:
            max_diff = max(max_diff, d)
        if not ok:
            reasons.append(f"{col}: {why}")

    # Factor levels, row names, and the ts start/end/frequency are part of the data set.
    ref_levels = entry.get("levels") or {}
    if ref_levels and {k: list(v) for k, v in ds.factor_levels(name).items()} != {
        k: list(v) for k, v in ref_levels.items()
    }:
        reasons.append("factor levels differ")
    ref_rn = entry.get("rownames")
    py_rn = ds.row_names(name)
    if (ref_rn is None) != (py_rn is None) or (ref_rn is not None and list(ref_rn) != py_rn):
        reasons.append("row names differ")

    return not reasons, max_diff, n_values, reasons


def _time_ms(fn, repeats=20):
    fn()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times)


def main() -> int:
    lines = []
    total_r = 0.0
    total_py = 0.0
    all_ok = True
    overall_max = 0.0
    total_values = 0
    names = sorted(REF)
    for name in names:
        entry = REF[name]
        ok, max_diff, n_values, reasons = _check(name, entry)
        py_ms = _time_ms(lambda n=name: ds.load(n))
        r_ms = float(entry["ms"])
        total_r += r_ms
        total_py += py_ms
        all_ok &= ok
        overall_max = max(overall_max, max_diff)
        total_values += n_values
        status = "yes" if ok else "no"
        detail = "" if ok else " | " + "; ".join(reasons)
        lines.append(
            f"case {name}: matches {status} values {n_values} max_abs_diff {max_diff:.3g} "
            f"r_ms {r_ms:.3f} translated_ms {py_ms:.3f}{detail}"
        )
    summary = [
        f"data sets {len(names)}, values {total_values}",
        f"matches {'yes' if all_ok else 'no'}",
        f"max_abs_diff {overall_max!r}",
        f"r_ms {total_r:.3f}",
        f"translated_ms {total_py:.3f}",
        f"speedup {total_r / total_py:.3f}",
    ]
    report = "\n".join(lines + [""] + summary) + "\n"
    (OUT / "datasets-compare.txt").write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
