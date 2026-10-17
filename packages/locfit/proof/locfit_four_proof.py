"""Proof and timing for the four open locfit functions: crit, hatmatrix, kappa0, lcv.

Run from the repository root with the workspace venv (it has the locfit crate):

    .venv/bin/python packages/locfit/proof/locfit_four_proof.py

R values and timings come from locfit_four_r.R (run it first). Inputs are
docs/output/locfit_kernel_inputs.csv. Timing: one untimed call, then the median
of 20 timed calls, time.perf_counter(). speedup = r_ms / translated_ms.

A case that raises is recorded as matches=no with the exception name. The
other cases still run.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "packages" / "locfit"
OUT = PKG / "docs" / "output"
TOL = 1e-8
PROOF = "packages/locfit/proof/locfit_four_proof.py"

spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None, is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated

from locfit_translated.locfit_raw import locfit_raw  # noqa: E402,F401

# hatmatrix.py and lcv.py import the bare name `locfit_raw`; alias it.
sys.modules["locfit_raw"] = sys.modules["locfit_translated.locfit_raw"]



def load(name, relpath):
    module_spec = importlib.util.spec_from_file_location(name, PKG / relpath)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


crit = load("locfit_four_crit", "locfit/crit.py").crit
hatmatrix = load("locfit_four_hatmatrix", "locfit/hatmatrix.py").hatmatrix
kappa0 = load("locfit_four_kappa0", "locfit/kappa0.py").kappa0
lcv = load("locfit_four_lcv", "locfit/lcv.py").lcv

inp = np.genfromtxt(OUT / "locfit_kernel_inputs.csv", delimiter=",", names=True)
x = inp["x"]
y = inp["y"]
n = len(y)


def read_pairs(path):
    pairs = {}
    for line in path.read_text().splitlines():
        name, text = line.split(",", 1)
        pairs[name] = text
    return pairs


def values(text):
    return np.array([float(v) for v in text.split(",")])


def timed_ms(fn):
    fn()  # one untimed call
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def max_diff(got, want):
    got = np.asarray(got, dtype=float).reshape(-1)
    if got.shape != want.shape:
        return float("inf")
    return float(np.max(np.abs(got - want)))


def lcv_vector(out):
    return np.array([out["lik"], out["infl"], out["vari"], out["cv"]])


def run_case(label, call, to_got, want, r_ms):
    try:
        out = call()
        diff = max_diff(to_got(out), want)
        py_ms = timed_ms(call)
        matches = "yes" if diff <= TOL else "no"
        return (f"{label},matches={matches},max_abs_diff={diff:.3e},"
                f"r_ms={r_ms:.6g},translated_ms={py_ms:.6g},"
                f"speedup={r_ms / py_ms:.6g},proof={PROOF}")
    except Exception as exc:  # noqa: BLE001  (record the blocker, keep going)
        return (f"{label},matches=no,max_abs_diff=inf,r_ms={r_ms:.6g},"
                f"translated_ms=nan,speedup=nan,"
                f"error={type(exc).__name__}: {str(exc).splitlines()[0]},"
                f"proof={PROOF}")


def main():
    ref = {k: values(v) for k, v in read_pairs(OUT / "locfit_four_r_values.txt").items()}
    r_ms = {k: float(v) for k, v in read_pairs(OUT / "locfit_four_r_timing.txt").items()}

    rows = [
        run_case("crit d=1 cov=0.95 (crit.val)",
                 lambda: crit(const=(0.0, 1.0), d=1, cov=0.95),
                 lambda out: [out.crit_val], ref["crit_d1"], r_ms["crit_d1"]),
        run_case("crit d=1 cov=0.90 (crit.val)",
                 lambda: crit(const=(0.0, 1.0), d=1, cov=0.9),
                 lambda out: [out.crit_val], ref["crit_d1_cov090"], r_ms["crit_d1_cov090"]),
        run_case("crit d=2 cov=0.95 (crit.val)",
                 lambda: crit(const=(0.0, 1.0), d=2, cov=0.95),
                 lambda out: [out.crit_val], ref["crit_d2"], r_ms["crit_d2"]),
        run_case("hatmatrix (t(locfit.raw geth=1, ev=dat()))",
                 lambda: hatmatrix(x=x, y=y),
                 lambda out: out, ref["hatmatrix"], r_ms["hatmatrix"]),
        run_case("kappa0 (default lfgrid(20))",
                 lambda: kappa0({"x": x, "y": y}, cov=0.95),
                 lambda out: [out.crit_val], ref["kappa0_default"], r_ms["kappa0_default"]),
        run_case("lcv (ev=dat())",
                 lambda: lcv(x, y, ev={"type": "data"}),
                 lcv_vector, ref["lcv_dat"], r_ms["lcv_dat"]),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    text = "\n".join(rows) + "\n"
    (OUT / "locfit_four_compare.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
