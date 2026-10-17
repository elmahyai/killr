"""Proof for the kernel batch: sfitted (fitted.locfit), locfit.quasi,
locfit.robust, locfit.censor, lscv.exact against R locfit 1.5-9.12.

Also covers lscv (R's density LSCV, geth = 6) with ev = dat(), at degrees 0,
1, 2 and one alpha. R's default ev = rbox() is not verified (kd-tree).

Run from the repository root with the workspace venv (it has the crate):

    .venv/bin/python packages/locfit/proof/kernel_proof.py

R's reference values and timings come from kernel_r.R (same fixed inputs,
written by kernel_inputs_r.R). The translated functions run with the explicit
ev = {"type": "data"}, the same fit R makes with ev = dat(). R's default
ev = rbox() needs kd-tree interpolation, which crates/locfit does not have, so
the default path is not verified here.

Timing: one untimed call, then the median of 20 samples; each sample is a loop
of K calls, and the reported time is the sample time divided by K.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

import locfit as crate  # noqa: F401  (the compiled kernel; import check)

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "packages" / "locfit"
OUT = PKG / "docs" / "output"
TOL = 1e-8
K = 20
DATA_EV = {"type": "data"}

spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None, is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated

from locfit_translated.locfit_censor import locfit_censor  # noqa: E402
from locfit_translated.locfit_quasi import locfit_quasi  # noqa: E402
from locfit_translated.locfit_robust import locfit_robust  # noqa: E402
from locfit_translated.locfit_raw import fitted, locfit_raw  # noqa: E402
from locfit_translated.lscv_exact import lscv_exact  # noqa: E402
from locfit_translated.lscv import lscv  # noqa: E402

inp = np.genfromtxt(OUT / "locfit_kernel_inputs.csv", delimiter=",", names=True)
x = inp["x"]
y = inp["y"]
cens = inp["cens"]
w = inp["w"]
dsamp = np.genfromtxt(OUT / "locfit_kernel_dsamp.csv", delimiter=",", names=True)["dsamp"]


def read_r_values():
    vals = {}
    for line in (OUT / "locfit_kernel_r_values.txt").read_text().splitlines():
        name, text = line.split(",", 1)
        vals[name] = np.array([float(v) for v in text.strip('"').split(",")])
    return vals


def read_r_timing():
    times = {}
    for line in (OUT / "locfit_kernel_r_timing.txt").read_text().splitlines():
        name, value = line.split(",", 1)
        times[name] = float(value)
    return times


def timed_ms(fn):
    fn()  # one untimed call
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(K):
            fn()
        samples.append((time.perf_counter() - start) * 1000.0 / K)
    return statistics.median(samples)


CALLS = {
    "sfitted": lambda: fitted(locfit_raw(x.reshape(-1, 1), y, ev=DATA_EV)),
    "quasi": lambda: fitted(locfit_quasi(x.reshape(-1, 1), y, weights=w, ev=DATA_EV)),
    "robust": lambda: fitted(locfit_robust(x.reshape(-1, 1), y, ev=DATA_EV)),
    "censor": lambda: fitted(locfit_censor(x.reshape(-1, 1), y, cens, ev=DATA_EV)),
    "lscv_exact_h05": lambda: lscv_exact(dsamp, h=0.5),
    "lscv_exact_h03": lambda: lscv_exact(dsamp, h=0.3),
    "lscv_dat_deg2": lambda: lscv(dsamp, ev=DATA_EV),
    "lscv_dat_deg1": lambda: lscv(dsamp, ev=DATA_EV, deg=1),
    "lscv_dat_deg0": lambda: lscv(dsamp, ev=DATA_EV, deg=0),
    "lscv_dat_alpha05": lambda: lscv(dsamp, ev=DATA_EV, alpha=0.5),
}

# The R function each row checks, for the comparison file.
ROW_FN = {
    "sfitted": "sfitted (fitted.locfit)",
    "quasi": "locfit.quasi",
    "robust": "locfit.robust",
    "censor": "locfit.censor",
    "lscv_exact_h05": "lscv.exact",
    "lscv_exact_h03": "lscv.exact",
    "lscv_dat_deg2": "lscv",
    "lscv_dat_deg1": "lscv",
    "lscv_dat_deg0": "lscv",
    "lscv_dat_alpha05": "lscv",
}


def main():
    ref = read_r_values()
    r_ms = read_r_timing()
    lines = []
    for name, call in CALLS.items():
        got = np.asarray(call(), dtype=float).reshape(-1)
        want = ref[name]
        if got.shape != want.shape:
            diff = float("inf")
        else:
            diff = float(np.max(np.abs(got - want)))
        matches = "yes" if diff <= TOL else "no"
        py_ms = timed_ms(CALLS[name])
        lines.append(
            f"{ROW_FN[name]},case={name},matches={matches},max_abs_diff={diff:.3e},"
            f"r_ms={r_ms[name]:.6g},translated_ms={py_ms:.6g},"
            f"speedup={r_ms[name] / py_ms:.6g},"
            f"proof=packages/locfit/proof/kernel_proof.py")
    text = "\n".join(lines) + "\n"
    (OUT / "locfit_kernel_compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
