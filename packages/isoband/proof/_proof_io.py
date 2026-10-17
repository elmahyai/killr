"""Shared helpers for the isoband proof scripts (R versus Python).

Each proof prints its own results as lines of tab-separated fields. R writes the
same format to ``docs/output/<name>-r.txt``:

- ``r_ms <milliseconds>``: median of 20 timed calls (``Sys.time()``).
- ``L case name n``: the length of a result vector or column.
- ``V case name row value``: one numeric value (``%.17g``).
- ``T case name row text``: one text value.

The Python proof compares its values with the R file within ``TOL``.
"""

from __future__ import annotations

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

TOL = 1e-8
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "output"


def emit_fields(lines: list[str], case: str, fields: dict) -> None:
    """Append the L, V, and T lines for each named vector in ``fields``."""
    for name, value in fields.items():
        arr = np.asarray(value).reshape(-1)
        lines.append(f"L\t{case}\t{name}\t{arr.size}")
        if arr.dtype.kind in "USO":
            for i, text in enumerate(arr, start=1):
                lines.append(f"T\t{case}\t{name}\t{i}\t{text}")
        else:
            for i, v in enumerate(arr.astype(np.float64).tolist(), start=1):
                lines.append(f"V\t{case}\t{name}\t{i}\t{v:.17g}")


def parse(lines: list[str]):
    lengths: dict = {}
    values: dict = {}
    texts: dict = {}
    for line in lines:
        parts = line.split("\t")
        if parts[0] == "L":
            lengths[(parts[1], parts[2])] = int(parts[3])
        elif parts[0] == "V":
            values[(parts[1], parts[2], int(parts[3]))] = float(parts[4])
        elif parts[0] == "T":
            texts[(parts[1], parts[2], int(parts[3]))] = parts[4]
    return lengths, values, texts


def compare(py_lines: list[str], r_lines: list[str]) -> tuple[bool, float]:
    """Return (matched, max_abs_diff) for the numeric and text values."""
    lp, vp, tp = parse(py_lines)
    lr, vr, tr = parse(r_lines)
    matched = lp == lr and set(vp) == set(vr) and tp == tr
    max_diff = 0.0
    for key in set(vp) & set(vr):
        d = abs(vp[key] - vr[key])
        if math.isnan(d):
            matched = False
        else:
            max_diff = max(max_diff, d)
    if max_diff > TOL:
        matched = False
    return matched, max_diff


def run_proof(name: str, cases, timing_cases, run_all, emit) -> None:
    """Run ``run_all`` once untimed on ``cases``, then time 20 calls on ``timing_cases``.

    ``emit(res, cases)`` gives the output lines. The lines go to stdout (redirect them
    to ``docs/output/<name>-python.txt``). The comparison with R goes to stderr.
    """
    res = run_all(cases)  # untimed call
    elapsed = []
    for _ in range(20):
        t0 = time.perf_counter()
        run_all(timing_cases)
        elapsed.append(time.perf_counter() - t0)
    py_ms = statistics.median(elapsed) * 1000
    py_lines = emit(res, cases)
    print(f"py_ms {py_ms:.17g}")
    print("\n".join(py_lines))

    r_lines = (OUT_DIR / f"{name}-r.txt").read_text().splitlines()
    r_ms = float(next(line for line in r_lines if line.startswith("r_ms")).split()[1])
    matched, max_diff = compare(py_lines, r_lines)
    speedup = r_ms / py_ms if py_ms > 0 else float("nan")
    print(
        f"{name} matched={'yes' if matched else 'no'} max_abs_diff={max_diff:.3g} "
        f"r_ms={r_ms:.6g} py_ms={py_ms:.6g} speedup={speedup:.4g}",
        file=sys.stderr,
    )
