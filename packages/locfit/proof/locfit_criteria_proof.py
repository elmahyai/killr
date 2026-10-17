"""Proof and timing for the seven locfit helpers: aic, ang, cp, crit, dat,
expit, gcv.

Run from the repository root with the workspace venv (it has the locfit
crate, which supplies the direct fit):

    .venv/bin/python packages/locfit/proof/locfit_criteria_proof.py

The R values come from locfit_criteria_r.R, which calls the real R functions.
aic, cp, and gcv take a fit. The fit is the crate's direct local fit at the
data (ev = dat()), mapped to the locfit dp and mi names. The timed Python call
includes that fit, as R's aic(x, y, ev = dat()) does.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

import locfit as crate  # crates/locfit, the loaded C kernel

ROOT = Path(__file__).parents[3]
PKG = ROOT / "packages" / "locfit" / "locfit"
OUT = ROOT / "packages" / "locfit" / "docs" / "output"
TOL = 1e-8
K = 100

# Load the translated package as a namespace so its relative imports resolve.
spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None,
                                      is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated
from locfit_translated.aic import aic  # noqa: E402
from locfit_translated.ang import ang  # noqa: E402
from locfit_translated.cp import cp  # noqa: E402
from locfit_translated.crit import crit  # noqa: E402
from locfit_translated.dat import dat  # noqa: E402
from locfit_translated.expit import expit  # noqa: E402
from locfit_translated.gcv import gcv  # noqa: E402

X = np.linspace(0.0, 1.0, 12)
Y = np.sin(2 * np.pi * X) + 0.1 * np.cos(7 * X)


def direct_fit(x, y):
    """Direct local fit at the data, with the R names for dp and mi."""
    r = crate.locfit_fit(np.asarray(x, float).reshape(-1, 1),
                         np.asarray(y, float), kern="tricube", kt="spherical",
                         nn=0.7, deg=2)
    return {"dp": {"lk": float(r["lk"]), "df1": float(r["df0"]),
                   "df2": float(r["df1"])},
            "mi": {"n": float(len(y))}}


def values_of(obj):
    if isinstance(obj, dict):
        return np.asarray(list(obj.values()), dtype=float)
    return np.asarray(obj, dtype=float).reshape(-1)


def crit_value(**kwargs):
    return crit(**kwargs).crit_val


def dat_vector(cv=False):
    z = dat(cv)
    return np.array([float(z["type"] == "crossval"), z["xev"], z["mg"],
                     z["cut"], z["ll"], z["ur"]])


CALLS = {
    "aic": lambda: aic(direct_fit(X, Y)),
    "cp": lambda: cp(direct_fit(X, Y), sig2=1),
    "gcv": lambda: gcv(direct_fit(X, Y)),
    "crit": lambda: crit_value(const=(0.0, 1.0), d=1, cov=0.95),
    "crit_cov090": lambda: crit_value(const=(0.0, 1.0), d=1, cov=0.9),
    "crit_d2": lambda: crit_value(const=(0.0, 1.0), d=2, cov=0.95),
    "dat": lambda: dat_vector(False),
    "dat_cv": lambda: dat_vector(True),
    "expit": lambda: expit(np.array([-3.0, 0.0, 2.0])),
    "ang": lambda: ang(np.array([-1.0, 0.0, 1.0])),
}
TIMED = ["aic", "cp", "gcv", "crit", "dat", "expit", "ang"]


def timed(fn):
    fn()  # one untimed call
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(K):
            fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples) / K


def load_r_values():
    ref = {}
    for line in (OUT / "locfit_criteria_r_values.txt").read_text().splitlines():
        name, values = line.split(",", 1)
        ref[name] = np.array([float(v) for v in values.split(",")])
    return ref


def load_r_timing():
    times = {}
    for line in (OUT / "locfit_criteria_r_timing.txt").read_text().splitlines():
        name, value = line.split(",", 1)
        times[name] = float(value)
    return times


def main():
    ref = load_r_values()
    r_ms = load_r_timing()
    lines = []
    for name, call in CALLS.items():
        try:
            value = values_of(call())
        except NotImplementedError as exc:
            lines.append(f"{name},matches=no,max_abs_diff=NA,r_ms=NA,"
                         f"translated_ms=NA,speedup=NA,blocked_by={exc}")
            continue
        expected = ref[name]
        if value.shape != expected.shape:
            diff = float("inf")
        else:
            diff = float(np.max(np.abs(value - expected)))
        matches = "yes" if diff <= TOL else "no"
        (OUT / f"locfit_{name}_python.txt").write_text(
            "\n".join(f"{v:.17g}" for v in value) + "\n")
        if name in TIMED:
            tms = timed(call)
            lines.append(f"{name},matches={matches},max_abs_diff={diff:.17g},"
                         f"r_ms={r_ms[name]:.17g},translated_ms={tms:.17g},"
                         f"speedup={r_ms[name] / tms:.17g}")
        else:
            lines.append(f"{name},matches={matches},max_abs_diff={diff:.17g},"
                         f"r_ms=NA,translated_ms=NA,speedup=NA")
    (OUT / "locfit_criteria_compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
