"""Proof for the gower Rust kernel: compare against R gower 1.0.2 on the same inputs.

Run from the repository root, after make_inputs.py and proof_r.R:

    .venv/bin/python packages/gower/proof/proof_python.py

Reads the inputs in packages/gower/proof/data/ and the R results written by
proof_r.R. It does not call R. Writes the comparison to
packages/gower/docs/output/proof.txt.

The argument preparation in `prepare` follows gower_work's explicit
pair_x / pair_y branch: pairing, per-pair ranges, factor flags, and the
0-based pair with -1 for skipped columns. The timed calls include it, so
they match the R calls.
"""

import csv
import math
import os
import statistics
import time
import warnings

import numpy as np

import gower_kernel as gk

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(os.path.dirname(HERE), "docs", "output")

LEVELS = ["a", "b", "c", "d"]
X_KINDS = ["dbl", "int", "lgl", "fct", "str", "dbl", "int", "dbl"]
Y_KINDS = ["dbl", "int", "lgl", "fct", "str", "dbl", "int"]
FACTOR = [0, 0, 0, 1, 0, 0, 0, 0]
PAIR_X = list(range(1, 9))
PAIR_Y = [2, 1, 3, 4, 5, 6, 7, 0]
WEIGHTS = np.array([1, 2, 0.5, 1.5, 1, 3, 0.25, 1], dtype=np.float64)
EPS = 1e-8
N_TOP = 5
N_REPS = 20
TOL = 1e-8


def parse(text, kind):
    if kind == "dbl":
        return math.nan if text == "NA" else float(text)
    if kind == "int":
        return -2147483648 if text == "NA" else int(text)
    if kind == "lgl":
        return -2147483648 if text == "NA" else (1 if text == "TRUE" else 0)
    if kind == "fct":
        return -2147483648 if text == "NA" else LEVELS.index(text) + 1
    if kind == "str":
        return None if text == "NA" else text
    raise ValueError(kind)


def read_cols(path, kinds):
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        rows = list(reader)
    cols = []
    for c, kind in enumerate(kinds):
        vals = [parse(r[c], kind) for r in rows]
        if kind == "dbl":
            cols.append(("dbl", np.array(vals, dtype=np.float64)))
        elif kind == "str":
            cols.append(("str", vals))
        else:
            cols.append(("lgl" if kind == "lgl" else "int", np.array(vals, dtype=np.int32)))
    return cols


def prepare(xc, yc):
    ncol = len(xc)
    pair = [0] * ncol
    for px, py in zip(PAIR_X, PAIR_Y):
        pair[px - 1] = py
    ranges = np.zeros(ncol, dtype=np.float64)
    for i, p in enumerate(pair):
        if p > 0:
            ranges[i] = gk.xy_range(xc[i], yc[p - 1])
    pair0 = np.array([p - 1 if p > 0 else -1 for p in pair], dtype=np.int64)
    factor_pair = np.array(FACTOR, dtype=np.int32)
    return ranges, pair0, factor_pair


def run_dist(xc, yc):
    ranges, pair0, fp = prepare(xc, yc)
    return gk.gower_dist(xc, yc, ranges, pair0, fp, EPS, WEIGHTS, 1)


def run_topn(xc, yc):
    ranges, pair0, fp = prepare(xc, yc)
    return gk.gower_topn(xc, yc, ranges, pair0, fp, N_TOP, EPS, WEIGHTS, 1)


def time_median(fn):
    fn()  # one untimed call
    secs = []
    for _ in range(N_REPS):
        t0 = time.perf_counter()
        fn()
        secs.append(time.perf_counter() - t0)
    return statistics.median(secs), secs


def read_floats(path):
    out = []
    with open(path) as fh:
        for line in fh:
            for tok in line.split():
                out.append(math.nan if tok in ("NaN", "NA") else float(tok))
    return np.array(out, dtype=np.float64)


def read_int_matrix(path):
    with open(path) as fh:
        return np.array([[int(t) for t in line.split()] for line in fh if line.strip()], dtype=np.int64)


def read_float_matrix(path):
    with open(path) as fh:
        return np.array([[float(t) for t in line.split()] for line in fh if line.strip()], dtype=np.float64)


def max_abs_diff(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    if a.shape != b.shape:
        return math.inf
    both_nan = np.isnan(a) & np.isnan(b)
    diff = np.abs(a - b)
    diff[both_nan] = 0.0
    if np.any(np.isnan(a) != np.isnan(b)):
        return math.inf
    return float(diff.max()) if diff.size else 0.0


def main():
    xc = read_cols(os.path.join(DATA, "x.csv"), X_KINDS)
    yc = read_cols(os.path.join(DATA, "y.csv"), Y_KINDS)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dist = np.asarray(run_dist(xc, yc))
        topn_index, topn_dist = run_topn(xc, yc)
    n_warn = len(caught)

    r_dist = read_floats(os.path.join(DATA, "r_dist.txt"))
    r_index = read_int_matrix(os.path.join(DATA, "r_topn_index.txt"))
    r_topn_dist = read_float_matrix(os.path.join(DATA, "r_topn_distance.txt"))
    r_times = {}
    with open(os.path.join(DATA, "r_timings.txt")) as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    r_times["gower_dist"] = float(lines[0].split()[1])
    r_times["gower_topn"] = float(lines[2].split()[1])

    dist_diff = max_abs_diff(dist, r_dist)
    topn_diff = max_abs_diff(topn_dist, r_topn_dist)
    index_mismatch = int(np.sum(np.asarray(topn_index, dtype=np.int64) != r_index))

    py_dist_median, _ = time_median(lambda: run_dist(xc, yc))
    py_topn_median, _ = time_median(lambda: run_topn(xc, yc))

    ok = dist_diff <= TOL and topn_diff <= TOL and index_mismatch == 0
    lines_out = [
        "gower Rust kernel vs gower 1.0.2 (R), same fixed inputs",
        f"inputs: x {len(xc[0][1])} rows x {len(xc)} cols, y {len(yc[0][1])} rows x {len(yc)} cols, "
        f"pairs {PAIR_Y} (0 = skipped), eps {EPS}, weights {WEIGHTS.tolist()}",
        f"gower_dist: {dist.size} values, max abs diff {dist_diff:.3e}",
        f"gower_topn: {N_TOP} x {topn_index.shape[1]}, max abs diff in distance {topn_diff:.3e}, "
        f"index mismatches {index_mismatch}",
        f"python warnings during the untimed call: {n_warn}",
        f"timings (median of {N_REPS} calls after 1 untimed):",
        f"  gower_dist  R {r_times['gower_dist']:.6f} s   Rust {py_dist_median:.6f} s   "
        f"speedup (R/Python) {r_times['gower_dist'] / py_dist_median:.2f}",
        f"  gower_topn  R {r_times['gower_topn']:.6f} s   Rust {py_topn_median:.6f} s   "
        f"speedup (R/Python) {r_times['gower_topn'] / py_topn_median:.2f}",
        f"tolerance {TOL:g}: {'PASS' if ok else 'FAIL'}",
    ]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "proof.txt"), "w") as fh:
        fh.write("\n".join(lines_out) + "\n")
    print("\n".join(lines_out))


if __name__ == "__main__":
    main()
