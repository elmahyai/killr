"""Shared Python side of the shuffle proofs.

Mirrors shuffle-harness-r.R: the same seed and call order, one runif-style
draw after each call, the same value lines, and a median of 20 timed passes
with perf_counter. Then compares against the R values file.
"""

from __future__ import annotations

import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from permute._rng import set_seed, unif_rand  # noqa: E402

TOLERANCE = 1e-8


@dataclass
class Case:
    name: str
    seed: int
    f: Callable[[], object]


def _run_one(case: Case):
    set_seed(case.seed)
    res = case.f()
    values = [float(v) for v in np.ravel(np.asarray(res))]
    return values + [unif_rand()]


def _format(values):
    return ",".join(f"{v:.17g}" for v in values)


def _read_values(path: Path):
    out = {}
    for line in path.read_text().splitlines():
        name, body = line.split("\t", 1)
        out[name] = [float(x) for x in body.split(",")] if body else []
    return out


def run_proof(fn_name: str, cases: list[Case], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    values_path = out_dir / f"{fn_name}-py-values.txt"
    timing_path = out_dir / f"{fn_name}-py-timing.tsv"
    r_values_path = out_dir / f"{fn_name}-r-values.txt"
    r_timing_path = out_dir / f"{fn_name}-r-timing.tsv"

    py_values = {c.name: _run_one(c) for c in cases}
    values_path.write_text(
        "".join(f"{c.name}\t{_format(py_values[c.name])}\n" for c in cases)
    )

    def one_pass() -> float:
        total = 0.0
        for c in cases:
            set_seed(c.seed)
            t0 = time.perf_counter()
            c.f()
            total += (time.perf_counter() - t0) * 1000.0
        return total

    one_pass()  # untimed
    py_ms = statistics.median(one_pass() for _ in range(20))
    timing_path.write_text(f"function\tpy_ms\n{fn_name}\t{py_ms:.9f}\n")

    r_values = _read_values(r_values_path)
    r_ms = float(r_timing_path.read_text().splitlines()[1].split("\t")[1])

    max_diff = 0.0
    matches = True
    detail = []
    for c in cases:
        rv = r_values.get(c.name)
        pv = py_values[c.name]
        if rv is None or len(rv) != len(pv):
            matches = False
            max_diff = float("inf")
            detail.append(f"{c.name}: shape differs")
            continue
        diff = max((abs(a - b) for a, b in zip(rv, pv)), default=0.0)
        max_diff = max(max_diff, diff)
        if diff > TOLERANCE:
            matches = False
        detail.append(f"{c.name}: {diff}")

    speedup = r_ms / py_ms if py_ms else float("inf")
    result_path = out_dir / f"{fn_name}-result.txt"
    with result_path.open("w") as fh:
        fh.write("function,cases,matches,max_abs_diff,r_ms,translated_ms,speedup\n")
        fh.write(
            f"{fn_name},{len(cases)},{'yes' if matches else 'no'},{max_diff:.17g},"
            f"{r_ms:.9f},{py_ms:.9f},{speedup:.9f}\n"
        )
    print(f"{fn_name}: matches={'yes' if matches else 'no'} max_abs_diff={max_diff:.3g} "
          f"r_ms={r_ms:.6f} translated_ms={py_ms:.6f} speedup={speedup:.3f}")
    for d in detail:
        print("  " + d)
    return {"matches": matches, "max_abs_diff": max_diff, "r_ms": r_ms,
            "translated_ms": py_ms, "speedup": speedup}
