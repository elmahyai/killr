"""Proof: mclust.mclust_object.Mclust against R mclust 6.1.3 on the same fixed inputs.

Run from packages/mclust, after proof/Mclust-r.R:
    Rscript proof/Mclust-r.R && .venv/bin/python proof/Mclust-py.py
Writes docs/output/Mclust-py.txt with the same record layout as Mclust-r.txt.
"""

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mclust.mclust_object import Mclust  # noqa: E402

# Fixed inputs. Same as proof/Mclust-r.R.
xa_bank = np.loadtxt(ROOT / "proof" / "mclust_fit_banknote6.csv", delimiter=",")
ib = np.arange(1, 61)
xb = np.column_stack([((ib * 37) % 11) / 11 + 0.05 * ib / 60,
                      ((ib * 23) % 13) / 13 - 0.1 * ib / 60])
ia = np.arange(1, 41)
xc = ((ia * 37) % 11) / 11 + 0.1 * ia / 40
xf = np.concatenate([((ia * 37) % 11) / 11 + 0.1 * ia / 40, 5 + ((ia * 23) % 13) / 13 - 0.1 * ia / 40])


def fmt(v):
    if v is None:
        return "NULL"
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
        arr = np.asarray(x, dtype=float).ravel(order="F")
    return "\t".join([key] + [fmt(v) for v in arr])


def emit_fit(prefix, fit):
    v = fit["parameters"]["variance"]
    var_vals = v["sigmasq"] if "sigmasq" in v else v["sigma"]
    bic_mat = np.asarray(fit["BIC"]["values"], dtype=float)
    return [
        rec(f"{prefix}\tmodelName", fit["modelName"]),
        rec(f"{prefix}\tn", fit["n"]),
        rec(f"{prefix}\td", fit["d"]),
        rec(f"{prefix}\tG", fit["G"]),
        rec(f"{prefix}\tBICdim", list(bic_mat.shape)),
        rec(f"{prefix}\tBIC", bic_mat),
        rec(f"{prefix}\tloglik", fit["loglik"]),
        rec(f"{prefix}\tbic", fit["bic"]),
        rec(f"{prefix}\ticl", fit["icl"]),
        rec(f"{prefix}\tdf", fit["df"]),
        rec(f"{prefix}\thypvol", fit["hypvol"]),
        rec(f"{prefix}\tpro", fit["parameters"]["pro"]),
        rec(f"{prefix}\tmean", fit["parameters"]["mean"]),
        rec(f"{prefix}\tvariance", var_vals),
        rec(f"{prefix}\tz", fit["z"]),
        rec(f"{prefix}\tclassification", fit["classification"]),
        rec(f"{prefix}\tuncertainty", fit["uncertainty"]),
    ]


def one():
    return {
        "A": Mclust(xa_bank),
        "B": Mclust(xb),
        "C": Mclust(xc),
        "D": Mclust(xb, G=[1], modelNames=["EII", "VII", "EEE", "VVV"]),
        "E": Mclust(xc, G=[1], modelNames=["E", "V"]),
        "F": Mclust(xf),
    }


if __name__ == "__main__":
    fits = one()  # one untimed call; its records are written
    lines = []
    for key in ["A", "B", "C", "D", "E", "F"]:
        lines += emit_fit(key, fits[key])

    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000.0)
    lines.append(f"time_ms\t{'%.17g' % statistics.median(elapsed)}")

    out = ROOT / "docs" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "Mclust-py.txt").write_text("\n".join(lines) + "\n")
    print("Python Mclust median ms:", statistics.median(elapsed))
