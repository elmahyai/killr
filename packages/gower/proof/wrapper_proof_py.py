"""Wrapper-level proof, Python side: the public gower_dist and gower_topn
wrappers in packages/gower/gower against gower 1.0.2 in R, on the fixed
inputs written by make_inputs.py.

Run from the repository root, after wrapper_proof_r.R:

    .venv/bin/python packages/gower/proof/wrapper_proof_py.py

The extension must be built first:
    .venv/bin/maturin develop --release --manifest-path crates/gower/Cargo.toml

Inputs are passed as a pandas DataFrame, the way a user would call the
wrappers:
  - dbl columns: float64 with NaN for NA
  - factor column: pandas Categorical with levels a, b, c, d
  - character column: object column with None for NA
  - integer column: pandas Int64 with pd.NA for NA
  - logical column: pandas boolean with pd.NA for NA
  The wrapper keeps these as integer and logical storage, so R's gower_int
  and gower_logi run on them as they do in R.

Writes the Python values to packages/gower/proof/data/wrapper_py_*.txt and
the comparison to packages/gower/docs/output/wrapper_proof.txt.
Timing: time.perf_counter(), one untimed call, then the median of 20 timed
calls. The timed call is the whole public wrapper, including the column
conversion, the same as the R call.
"""

import csv
import math
import os
import statistics
import sys
import time
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)  # packages/gower, which holds the gower/ package
sys.path.insert(0, PKG)

from gower.gower_dist import gower_dist  # noqa: E402
from gower.gower_topn import gower_topn  # noqa: E402

DATA = os.path.join(HERE, "data")
OUT = os.path.join(os.path.dirname(HERE), "docs", "output")

LEVELS = ["a", "b", "c", "d"]
X_NAMES = [f"x{k}" for k in range(1, 9)]
Y_NAMES = [f"y{k}" for k in range(1, 8)]
X_KINDS = ["dbl", "int", "lgl", "fct", "str", "dbl", "int", "dbl"]
Y_KINDS = ["dbl", "int", "lgl", "fct", "str", "dbl", "int"]
PAIR_X = list(range(1, 9))
PAIR_Y = [2, 1, 3, 4, 5, 6, 7, 0]
WEIGHTS = np.array([1, 2, 0.5, 1.5, 1, 3, 0.25, 1], dtype=np.float64)
EPS = 1e-8
N_TOP = 5
N_REPS = 20
TOL = 1e-8


def load_frame(path, names, kinds):
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        rows = list(reader)
    cols = {}
    for c, (name, kind) in enumerate(zip(names, kinds)):
        text = [r[c] for r in rows]
        if kind == "dbl":
            cols[name] = np.array(
                [math.nan if t == "NA" else float(t) for t in text], dtype=np.float64
            )
        elif kind == "int":
            cols[name] = pd.array(
                [None if t == "NA" else int(t) for t in text], dtype="Int64"
            )
        elif kind == "lgl":
            cols[name] = pd.array(
                [None if t == "NA" else (t == "TRUE") for t in text], dtype="boolean"
            )
        elif kind == "fct":
            cols[name] = pd.Categorical(
                [None if t == "NA" else t for t in text], categories=LEVELS
            )
        elif kind == "str":
            cols[name] = pd.Series(
                [None if t == "NA" else t for t in text], dtype=object
            )
        else:
            raise ValueError(kind)
    return pd.DataFrame(cols, columns=names)


def run_dist(x, y):
    return gower_dist(
        x, y, pair_x=PAIR_X, pair_y=PAIR_Y, eps=EPS, weights=WEIGHTS, nthread=1
    )


def run_topn(x, y):
    return gower_topn(
        x, y, n=N_TOP, pair_x=PAIR_X, pair_y=PAIR_Y, eps=EPS,
        weights=WEIGHTS, nthread=1,
    )


def time_median(fn):
    fn()  # one untimed call
    secs = []
    for _ in range(N_REPS):
        t0 = time.perf_counter()
        fn()
        secs.append(time.perf_counter() - t0)
    return statistics.median(secs), secs


def fmt(v):
    return repr(float(v))


def write_floats(path, values):
    with open(path, "w") as fh:
        for v in np.asarray(values, dtype=np.float64).ravel():
            fh.write(fmt(v) + "\n")


def write_rows(path, matrix, kind):
    with open(path, "w") as fh:
        for row in np.asarray(matrix):
            if kind == "int":
                fh.write(" ".join(str(int(v)) for v in row) + "\n")
            else:
                fh.write(" ".join(fmt(v) for v in row) + "\n")


def read_floats(path):
    out = []
    with open(path) as fh:
        for line in fh:
            for tok in line.split():
                out.append(math.nan if tok in ("NaN", "NA") else float(tok))
    return np.array(out, dtype=np.float64)


def read_matrix(path, kind):
    with open(path) as fh:
        rows = [line.split() for line in fh if line.strip()]
    if kind == "int":
        return np.array([[int(t) for t in r] for r in rows], dtype=np.int64)
    return np.array([[float(t) for t in r] for r in rows], dtype=np.float64)


def max_abs_diff(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    if a.shape != b.shape:
        return math.inf
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    if np.any(nan_a != nan_b):
        return math.inf
    diff = np.abs(a - b)
    diff[nan_a & nan_b] = 0.0
    return float(diff.max()) if diff.size else 0.0


def read_r_timings(path):
    times = {}
    with open(path) as fh:
        for line in fh:
            name, value = line.split()
            times[name] = float(value)
    return times


def main():
    x = load_frame(os.path.join(DATA, "x.csv"), X_NAMES, X_KINDS)
    y = load_frame(os.path.join(DATA, "y.csv"), Y_NAMES, Y_KINDS)
    x5_before = x["x5"].tolist()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dist = run_dist(x, y)
        topn_index, topn_dist = run_topn(x, y)
    n_warn = len(caught)
    topn_index = np.asarray(topn_index)
    topn_dist = np.asarray(topn_dist)
    x5_unchanged = x["x5"].tolist() == x5_before

    write_floats(os.path.join(DATA, "wrapper_py_dist.txt"), dist)
    write_rows(os.path.join(DATA, "wrapper_py_topn_index.txt"), topn_index, "int")
    write_rows(os.path.join(DATA, "wrapper_py_topn_distance.txt"), topn_dist, "dbl")

    # Compare the two sides through the text files they wrote.
    r_dist = read_floats(os.path.join(DATA, "wrapper_r_dist.txt"))
    py_dist = read_floats(os.path.join(DATA, "wrapper_py_dist.txt"))
    r_index = read_matrix(os.path.join(DATA, "wrapper_r_topn_index.txt"), "int")
    py_index = read_matrix(os.path.join(DATA, "wrapper_py_topn_index.txt"), "int")
    r_tdist = read_matrix(os.path.join(DATA, "wrapper_r_topn_distance.txt"), "dbl")
    py_tdist = read_matrix(os.path.join(DATA, "wrapper_py_topn_distance.txt"), "dbl")

    dist_diff = max_abs_diff(py_dist, r_dist)
    if r_index.shape == py_index.shape:
        index_mismatch = int(np.sum(r_index != py_index))
    else:
        index_mismatch = -1
    topn_diff = max_abs_diff(py_tdist, r_tdist)

    r_times = read_r_timings(os.path.join(DATA, "wrapper_r_timings.txt"))
    py_dist_median, _ = time_median(lambda: run_dist(x, y))
    py_topn_median, _ = time_median(lambda: run_topn(x, y))
    x5_unchanged = x5_unchanged and x["x5"].tolist() == x5_before

    r_dist_ms = r_times["gower_dist"] * 1000
    r_topn_ms = r_times["gower_topn"] * 1000
    py_dist_ms = py_dist_median * 1000
    py_topn_ms = py_topn_median * 1000

    ok = (dist_diff <= TOL and topn_diff <= TOL and index_mismatch == 0
          and x5_unchanged)
    lines = [
        "gower public wrappers (Python) vs gower 1.0.2 (R), same fixed inputs",
        f"inputs: x {len(x)} rows x {x.shape[1]} cols, y {len(y)} rows x {y.shape[1]} cols, "
        f"pair_x {PAIR_X}, pair_y {PAIR_Y} (0 = skipped), eps {EPS:g}, "
        f"weights {WEIGHTS.tolist()}, n {N_TOP}, nthread 1",
        f"gower_dist: {dist.shape} values R {r_dist.size}, Python {py_dist.size}, "
        f"max abs diff {dist_diff:.3e}",
        f"gower_topn: index {py_index.shape} (R {r_index.shape}), "
        f"max abs diff in distance {topn_diff:.3e}, index mismatches {index_mismatch}",
        f"python warnings during the untimed call: {n_warn}",
        f"caller's x unchanged by the wrappers: {x5_unchanged}",
        f"timings (median of {N_REPS} calls after 1 untimed):",
        f"  gower_dist  r_ms {r_dist_ms:.3f}  translated_ms {py_dist_ms:.3f}  "
        f"speedup {r_dist_ms / py_dist_ms:.2f}",
        f"  gower_topn  r_ms {r_topn_ms:.3f}  translated_ms {py_topn_ms:.3f}  "
        f"speedup {r_topn_ms / py_topn_ms:.2f}",
        f"tolerance {TOL:g}: {'PASS' if ok else 'FAIL'}",
    ]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "wrapper_proof.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
