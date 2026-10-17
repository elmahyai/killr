from __future__ import annotations

import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lmom import pelgam, pelgev, pelglo, pelgno, pelgpa, pelgum, pelkap
from lmom import pelln3, pelnor, pelpe3, pelwak, pelwei, pelexp

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"
FUNCTIONS = {name: getattr(module, name) for module, name in (
    (pelexp, "pelexp"), (pelgam, "pelgam"), (pelgev, "pelgev"),
    (pelglo, "pelglo"), (pelgno, "pelgno"), (pelgpa, "pelgpa"),
    (pelgum, "pelgum"), (pelkap, "pelkap"), (pelln3, "pelln3"),
    (pelnor, "pelnor"), (pelpe3, "pelpe3"), (pelwak, "pelwak"),
    (pelwei, "pelwei"),
)}


def main() -> int:
    with (HERE / "pel_cases.csv").open(newline="") as handle:
        cases = list(csv.DictReader(handle))
    r_values = {}
    with (OUT / "pel_r_values.txt").open() as handle:
        next(handle)
        for line in handle:
            fn, index, value = line.split()
            r_values.setdefault(fn, {})[int(index)] = float(value)
    r_times = {}
    with (OUT / "pel_r_timings.txt").open() as handle:
        next(handle)
        for line in handle:
            fn, seconds = line.split()
            r_times[fn] = float(seconds)

    rows = []
    value_lines = ["fn index value"]
    for case in cases:
        fn = case["function"]
        x = np.asarray([float(v) for v in case["args"].split()], dtype=float)
        f = FUNCTIONS[fn]
        values = np.asarray(f(x), dtype=float)
        f(x)
        elapsed = []
        for _ in range(20):
            start = time.perf_counter()
            f(x)
            elapsed.append(time.perf_counter() - start)
        py_seconds = statistics.median(elapsed)
        diffs = [abs(values[i] - r_values[fn][i + 1]) for i in range(values.size)]
        max_diff = max(diffs, default=0.0)
        rows.append((fn, max_diff, r_times[fn] * 1000, py_seconds * 1000,
                     r_times[fn] / py_seconds))
        for i, value in enumerate(values, 1):
            value_lines.append(f"{fn} {i} {value:.17g}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pel_python_values.txt").write_text("\n".join(value_lines) + "\n")
    proof = ["lmom pel proof: R lmom 3.3 vs Python lmom wrappers",
             "tolerance: max absolute difference <= 1e-8",
             "function max_abs_diff r_ms translated_ms speedup"]
    for fn, diff, r_ms, py_ms, speedup in rows:
        proof.append(f"{fn} {diff:.17g} {r_ms:.9g} {py_ms:.9g} {speedup:.9g}")
    (OUT / "pel_proof.txt").write_text("\n".join(proof) + "\n")
    print("\n".join(proof))
    return 0 if all(row[1] <= 1e-8 for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
