"""Proof: mclust.density_mclust.densityMclust against R mclust 6.1.3 for the three gaps.

Run from packages/mclust, after proof/densityMclust-gaps-r.R:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/Mclust-gaps-py.py
Writes docs/output/densityMclust-gaps-py.txt with the same record layout as densityMclust-gaps-r.txt.
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
from mclust.density_mclust import densityMclust  # noqa: E402

# Fixed inputs. Same as proof/densityMclust-gaps-r.R.
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
    if isinstance(fit, str) and fit == "ERROR":
        return [f"{prefix}\terror\tERROR"]
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
        rec(f"{prefix}\tdensity", fit["density"]),
    ]


def _try(fn):
    """A case that R also rejects is recorded as ERROR on both sides (not a value)."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - the proof records the failure
        print("case error:", type(exc).__name__, str(exc), flush=True)
        return "ERROR"


def one():
    cases = {
        "A": lambda: densityMclust(xa_bank, plot=False),
        "B": lambda: densityMclust(xb, plot=False),
        "C": lambda: densityMclust(xc, plot=False),
        "D": lambda: densityMclust(xb, G=[1], modelNames=["EII", "VII", "EEE", "VVV"], plot=False),
        "E": lambda: densityMclust(xc, G=[1], modelNames=["E", "V"], plot=False),
        "F": lambda: densityMclust(xf, plot=False),
        "FA": lambda: densityMclust(xfa, plot=False),
        "BIG": lambda: (set_seed(2026), densityMclust(xg, plot=False))[1],
        "NB": lambda: densityMclust(xb, initialization={"noise": noise_b}, plot=False),
        "NC": lambda: densityMclust(xc, initialization={"noise": noise_c}, plot=False),
        "NBV": lambda: densityMclust(xb, initialization={"noise": noise_b}, Vinv=0.5, plot=False),
    }
    return {key: _try(fn) for key, fn in cases.items()}


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
    (out / "densityMclust-gaps-py.txt").write_text("\n".join(lines) + "\n")
    print("Python densityMclust gaps median ms:", statistics.median(elapsed))
