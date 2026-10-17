"""Proof: mclust.mclust_object.Mclust against R mclust 6.1.3 for the three gaps.

Run from packages/mclust, after proof/Mclust-gaps-r.R:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/Mclust-gaps-py.py
Writes docs/output/Mclust-gaps-py.txt with the same record layout as Mclust-gaps-r.txt.
The random stream (set.seed) is the ported R generator in packages/boot.
"""

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "boot"))
from boot.rng import set_seed  # noqa: E402
from mclust.mclust_object import Mclust  # noqa: E402

# Fixed inputs. Same as proof/Mclust-gaps-r.R.
xa_bank = np.loadtxt(ROOT / "proof" / "mclust_fit_banknote6.csv", delimiter=",")
ib = np.arange(1, 61)
xb = np.column_stack([((ib * 37) % 11) / 11 + 0.05 * ib / 60,
                      ((ib * 23) % 13) / 13 - 0.1 * ib / 60])
ia = np.arange(1, 41)
xc = ((ia * 37) % 11) / 11 + 0.1 * ia / 40
xf = np.concatenate([((ia * 37) % 11) / 11 + 0.1 * ia / 40, 5 + ((ia * 23) % 13) / 13 - 0.1 * ia / 40])
xfa = np.loadtxt(ROOT / "proof" / "mclust_faithful.csv", delimiter=",")
ig = np.arange(1, 2401)
xg = np.column_stack([np.sin(0.37 * ig + 1.3) + 0.4 * np.cos(0.11 * ig) + 3.0 * (ig > 1200),
                      np.cos(0.23 * ig) + 0.5 * np.sin(0.07 * ig)])
noise_b = [3, 17, 29, 44, 58]
noise_c = [2, 5, 9]

KEYS = ["A", "B", "C", "D", "E", "F", "FA", "BIG", "NB", "NC", "NBV"]


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
    arr = np.asarray(x, dtype=float).ravel(order="F")
    return "\t".join([key] + [fmt(v) for v in arr])


def emit_fit(prefix, fit):
    params = fit["parameters"]
    v = params["variance"] if params is not None else None
    var_vals = None
    if v is not None:
        var_vals = v["sigmasq"] if "sigmasq" in v else v["sigma"]
    return [
        rec(f"{prefix}\tmodelName", fit["modelName"]),
        rec(f"{prefix}\tn", fit["n"]),
        rec(f"{prefix}\td", fit["d"]),
        rec(f"{prefix}\tG", fit["G"]),
        rec(f"{prefix}\tBIC", np.asarray(fit["BIC"]["values"], dtype=float)),
        rec(f"{prefix}\tloglik", fit["loglik"]),
        rec(f"{prefix}\tbic", fit["bic"]),
        rec(f"{prefix}\ticl", fit["icl"]),
        rec(f"{prefix}\tdf", fit["df"]),
        rec(f"{prefix}\thypvol", fit["hypvol"]),
        rec(f"{prefix}\tpro", None if params is None else params["pro"]),
        rec(f"{prefix}\tmean", None if params is None else params["mean"]),
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
        "FA": Mclust(xfa),
        "BIG": (set_seed(2026), Mclust(xg))[1],
        "NB": Mclust(xb, initialization={"noise": noise_b}),
        "NC": Mclust(xc, initialization={"noise": noise_c}),
        "NBV": Mclust(xb, initialization={"noise": noise_b}, Vinv=0.5),
    }


if __name__ == "__main__":
    fits = one()  # one untimed call; its records are written
    lines = []
    for key in KEYS:
        lines += emit_fit(key, fits[key])

    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000.0)
    lines.append(f"time_ms\t{'%.17g' % statistics.median(elapsed)}")

    out = ROOT / "docs" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "Mclust-gaps-py.txt").write_text("\n".join(lines) + "\n")
    print("Python Mclust gaps median ms:", statistics.median(elapsed))
