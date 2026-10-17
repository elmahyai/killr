"""Proof: Python MclustBootstrap for types "wlbs", "pb" and "jk" against R mclust 6.1.3.

Run from packages/mclust, after proof/MclustBootstrap-types-r.R:
    Rscript proof/MclustBootstrap-types-r.R
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-types-py.py
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-types-compare.py
Writes docs/output/MclustBootstrap-types-py.txt with the same record layout as
MclustBootstrap-types-r.txt. For each type, the median of 20 timed calls
(time.perf_counter, seed 42) is the line <type> time_ms. Only the
MclustBootstrap call is timed; the fit is computed once outside the timing.
"""

import math
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "boot"))
warnings.simplefilter("ignore")

from boot.rng import set_seed  # noqa: E402
from mclust.bootstrap_family import MclustBootstrap  # noqa: E402
from mclust.mclust_object import Mclust  # noqa: E402

# Fixed input. Same as proof/MclustBootstrap-types-r.R.
ib = np.arange(1, 61)
xb = np.column_stack([((ib * 37) % 11) / 11 + 0.05 * ib / 60,
                      ((ib * 23) % 13) / 13 - 0.1 * ib / 60])
if len(np.unique(xb, axis=0)) != xb.shape[0]:
    raise SystemExit("fixed input must have no duplicate rows")


def fmt(v):
    v = float(v)
    if math.isnan(v):
        return "NA"
    return "%.17g" % v


def rec(key, x):
    if x is None:
        return f"{key}\tNULL"
    if isinstance(x, str):
        return f"{key}\t{x}"
    if isinstance(x, (list, tuple)):
        arr = np.asarray(x, dtype=float).ravel(order="F")
    else:
        arr = np.asarray(x, dtype=float).ravel(order="F") if not isinstance(x, (int, float)) else np.array([x], dtype=float)
    return "\t".join([key] + [fmt(v) for v in arr])


def run(type_, seed, fit):
    set_seed(seed)
    return MclustBootstrap(fit, type=type_)


def emit(type_, label, b):
    p = f"{type_}\t{label}"
    return [
        rec(f"{p}\tmodelName", b["modelName"]),
        rec(f"{p}\tG", b["G"]),
        rec(f"{p}\tnboot", b["nboot"]),
        rec(f"{p}\ttype", b["type"]),
        rec(f"{p}\tnonfit", b["nonfit"]),
        rec(f"{p}\tpar_pro", b["parameters"]["pro"]),
        rec(f"{p}\tpar_mean", b["parameters"]["mean"]),
        rec(f"{p}\tpar_variance", b["parameters"]["variance"]),
        rec(f"{p}\tpro", b["pro"]),
        rec(f"{p}\tmean", b["mean"]),
        rec(f"{p}\tvariance", b["variance"]),
    ]


if __name__ == "__main__":
    fit = Mclust(xb)
    lines = [
        rec("fit\tmodelName", fit["modelName"]),
        rec("fit\tG", fit["G"]),
    ]
    for type_ in ("wlbs", "pb", "jk"):
        lines += emit(type_, "seed42", run(type_, 42, fit))
        lines += emit(type_, "seed2026", run(type_, 2026, fit))
        elapsed = []
        for _ in range(20):
            started = time.perf_counter()
            run(type_, 42, fit)
            elapsed.append((time.perf_counter() - started) * 1000.0)
        lines.append(f"{type_}\ttime_ms\t{'%.17g' % statistics.median(elapsed)}")
        print(f"Python MclustBootstrap {type_} median ms:", statistics.median(elapsed))

    out = ROOT / "docs" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "MclustBootstrap-types-py.txt").write_text("\n".join(lines) + "\n")
