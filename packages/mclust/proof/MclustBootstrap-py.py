"""Proof: Python MclustBootstrap (type "bs", nboot = 999) against R mclust 6.1.3.

Run from packages/mclust, after proof/MclustBootstrap-r.R:
    Rscript proof/MclustBootstrap-r.R && /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-py.py
Writes docs/output/MclustBootstrap-py.txt with the same record layout as
MclustBootstrap-r.txt. The median of 20 timed calls (time.perf_counter) is on
the last line as time_ms. Only the MclustBootstrap call is timed; the fit is
computed once outside the timing, as in the R proof.
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

# Fixed input. Same as proof/MclustBootstrap-r.R.
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


def run(seed, fit):
    set_seed(seed)
    return MclustBootstrap(fit)


def emit(prefix, b):
    return [
        rec(f"{prefix}\tmodelName", b["modelName"]),
        rec(f"{prefix}\tG", b["G"]),
        rec(f"{prefix}\tnboot", b["nboot"]),
        rec(f"{prefix}\ttype", b["type"]),
        rec(f"{prefix}\tnonfit", b["nonfit"]),
        rec(f"{prefix}\tpar_pro", b["parameters"]["pro"]),
        rec(f"{prefix}\tpar_mean", b["parameters"]["mean"]),
        rec(f"{prefix}\tpar_variance", b["parameters"]["variance"]),
        rec(f"{prefix}\tpro", b["pro"]),
        rec(f"{prefix}\tmean", b["mean"]),
        rec(f"{prefix}\tvariance", b["variance"]),
    ]


if __name__ == "__main__":
    fit = Mclust(xb)
    # Untimed call (seed 42), plus seed 2026 as a second check on the same fit.
    b42 = run(42, fit)
    b2026 = run(2026, fit)
    lines = [
        rec("fit\tmodelName", fit["modelName"]),
        rec("fit\tG", fit["G"]),
    ]
    lines += emit("seed42", b42)
    lines += emit("seed2026", b2026)

    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        run(42, fit)
        elapsed.append((time.perf_counter() - started) * 1000.0)
    lines.append(f"time_ms\t{'%.17g' % statistics.median(elapsed)}")

    out = ROOT / "docs" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "MclustBootstrap-py.txt").write_text("\n".join(lines) + "\n")
    print("Python MclustBootstrap median ms:", statistics.median(elapsed))
