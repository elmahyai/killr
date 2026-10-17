"""Compare goftest_kernels (Rust, crates/goftest) with goftest 1.2-3 (R).

Run from the repository root after building the crate:
    .venv/bin/maturin develop --release --manifest-path crates/goftest/Cargo.toml
    Rscript packages/goftest/proof/ad-kernels-r.R
    .venv/bin/python packages/goftest/proof/ad-kernels-py.py

Reads the R values and timings from docs/output/ad-kernels-r.tsv. This script
does not call R.
"""

import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

import goftest_kernels as gk

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "packages" / "goftest" / "docs" / "output"
TOL = 1e-8
GOLDEN = 0.6180339887498949
FAMILIES = ["uniform", "skewed"]
NS = [5, 50, 1000]
GRID = 0.05 + 0.1 * np.arange(60, dtype=float)
BIG_GRID = 0.05 + 0.0005 * np.arange(10000, dtype=float)
BIG_N = 10000


def make_sample(n, family):
    i = np.arange(1, n + 1, dtype=float)
    if family == "uniform":
        u = (i * GOLDEN) % 1.0
    else:
        t = i / (n + 1)
        u = t * t
    return np.sort(u)


def python_values():
    vals = {}
    for fam in FAMILIES:
        for n in NS:
            u = make_sample(n, fam)
            stat, p = gk.ad_test(u)
            vals[f"ad_test_stat|{fam}|{n}"] = np.array([stat])
            vals[f"ad_test_p|{fam}|{n}"] = np.array([p])
    vals["adinf_approx|grid"] = gk.adinf(GRID)
    vals["adinf_exact|grid"] = gk.ad_inf(GRID)
    for n in NS:
        vals[f"ad_prob_n|{n}|grid"] = gk.ad_prob_n(GRID, n)
    return vals


def median_ms(f, reps=20):
    f()  # untimed call
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        f()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times)


def python_timings():
    u_big = make_sample(BIG_N, "uniform")
    return {
        "ad_test": median_ms(lambda: gk.ad_test(u_big)),
        "ad_prob_n": median_ms(lambda: gk.ad_prob_n(BIG_GRID, 50)),
        "adinf": median_ms(lambda: gk.adinf(BIG_GRID)),
        "ad_inf": median_ms(lambda: gk.ad_inf(BIG_GRID)),
    }


def read_r():
    values = defaultdict(dict)
    timings = {}
    with open(OUT / "ad-kernels-r.tsv") as f:
        header = next(f)
        assert header.strip() == "kind\tcase\tindex\tvalue", header
        for line in f:
            kind, case, idx, val = line.rstrip("\n").split("\t")
            if kind == "value":
                values[case][int(idx)] = float(val)
            elif kind == "time_ms":
                timings[case] = float(val)
    return values, timings


def main():
    r_vals, r_times = read_r()
    py_vals = python_values()

    if set(r_vals) != set(py_vals):
        missing = set(r_vals) ^ set(py_vals)
        raise SystemExit(f"case mismatch: {sorted(missing)}")

    lines = [
        "goftest 1.2-3 (R, compiled C) vs goftest_kernels (Rust, PyO3 + NumPy)",
        f"fixed samples: uniform and skewed, n = {NS}; grid of 60 quantiles; tolerance {TOL:g}",
        "",
        "value comparison (max abs diff per case):",
    ]
    diffs = []
    for case in sorted(py_vals):
        rv = np.array([r_vals[case][k] for k in sorted(r_vals[case])])
        pv = py_vals[case]
        if rv.shape != pv.shape:
            raise SystemExit(f"shape mismatch in {case}: {rv.shape} vs {pv.shape}")
        d = float(np.max(np.abs(rv - pv)))
        diffs.append(d)
        lines.append(f"  {case}\tlen={len(pv)}\tmax_abs_diff={d:.3e}")

    max_diff = float(np.max(diffs))
    passed = bool(max_diff <= TOL)
    lines += [
        "",
        f"max abs diff over all value cases: {max_diff:.3e}",
        f"result: {'PASS' if passed else 'FAIL'} (tolerance {TOL:g})",
        "",
        "timings (median of 20 calls after one untimed call, ms):",
        "  kernel\tR\tRust\tspeedup (R/Rust)",
    ]

    py_times = python_timings()
    for name in ["ad_test", "ad_prob_n", "adinf", "ad_inf"]:
        rt = r_times[name]
        pt = py_times[name]
        lines.append(f"  {name}\t{rt:.4f}\t{pt:.4f}\t{rt / pt:.2f}")

    text = "\n".join(lines) + "\n"
    (OUT / "ad-kernels.txt").write_text(text)
    print(text, end="")
    print(f"wrote {OUT / 'ad-kernels.txt'}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
