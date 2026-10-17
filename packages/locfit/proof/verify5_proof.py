"""Proof for the five-function check: hatmatrix, kappa0, kdeb, lcv, lf.

Compares each Python function with R locfit 1.5-9.12 on the explicit
ev = data path (ev = dat()), where the function takes ev. The R values and
timings come from verify5_r.R (same fixed inputs as the kernel batch).

Run from the repository root with the workspace venv:

    .venv/bin/python packages/locfit/proof/verify5_proof.py

Notes for the compare file:

- hatmatrix: R's hatmatrix() stops on every form tried, so the reference is the
  operator it asks locfit for, t(locfit.raw(..., geth = 1, ev = dat())). Its
  H %*% y equals the fitted values (checked in locfit_verify5_r_default.txt).
- kappa0: R's explicit ev = dat() gives a degenerate tube constant (R warns
  "Unknown integration type"). The meaningful R value is on the default
  ev = lfgrid(20) path, which needs the kd-tree grid. That value is in
  locfit_verify5_r_default.txt and is not compared.
- kdeb: the function has no ev argument, so its only path is the bandwidth
  selection on the data. R runs that selection in C (.C("kdeb")).
- lcv: explicit ev = dat(). The default ev = rbox() needs the kd-tree.
- lf: builds the smooth term with no fit. The Python default ev is
  {"type": "rbox"}; R's rbox() is type "tree" with cut 0.8. The proof compares
  the explicit path only.

A case whose Python call raises is recorded as matches=no with the exception
name in the row. The other rows still run.

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

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "packages" / "locfit"
OUT = PKG / "docs" / "output"
TOL = 1e-8
K = 20
DATA_EV = {"type": "data"}
PROOF = "packages/locfit/proof/verify5_proof.py"

# The package directory PKG is the fake package "locfit_translated", so that
# locfit_raw.py (which uses relative imports) loads as a submodule.
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


hatmatrix_mod = load("locfit_five_hatmatrix", "locfit/hatmatrix.py")
kappa0_mod = load("locfit_five_kappa0", "locfit/kappa0.py")
kdeb_mod = load("locfit_five_kdeb", "locfit/kdeb.py")
lcv_mod = load("locfit_five_lcv", "locfit/lcv.py")
lf_mod = load("locfit_five_lf", "locfit/lf.py")

inp = np.genfromtxt(OUT / "locfit_kernel_inputs.csv", delimiter=",", names=True)
x = inp["x"]
y = inp["y"]
dsamp = np.genfromtxt(OUT / "locfit_kernel_dsamp.csv", delimiter=",", names=True)["dsamp"]


def read_values():
    vals = {}
    for line in (OUT / "locfit_verify5_r_values.txt").read_text().splitlines():
        name, text = line.split(",", 1)
        vals[name] = np.array([float(v) for v in text.split(",")])
    return vals


def read_pairs(path):
    pairs = {}
    for line in path.read_text().splitlines():
        name, text = line.split(",", 1)
        pairs[name] = text
    return pairs


def timed_ms(fn):
    fn()  # one untimed call
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(K):
            fn()
        samples.append((time.perf_counter() - start) * 1000.0 / K)
    return statistics.median(samples)


def max_diff(got, want):
    got = np.asarray(got, dtype=float).reshape(-1)
    if got.shape != want.shape:
        return float("inf")
    return float(np.max(np.abs(got - want)))


def run_case(label, case, call, to_got, want, r_ms, extra_ok=lambda out: True):
    """Evaluate one case; return the compare row. A raised error is a no."""
    try:
        out = call()
        diff = max_diff(to_got(out), want)
        ok = extra_ok(out)
        py_ms = timed_ms(call)
        matches = "yes" if (diff <= TOL and ok) else "no"
        return (f"{label},case={case},matches={matches},max_abs_diff={diff:.3e},"
                f"r_ms={r_ms:.6g},translated_ms={py_ms:.6g},"
                f"speedup={r_ms / py_ms:.6g},proof={PROOF}")
    except Exception as exc:  # noqa: BLE001  (record the blocker, keep going)
        return (f"{label},case={case},matches=no,max_abs_diff=inf,"
                f"r_ms={r_ms:.6g},translated_ms=nan,speedup=nan,"
                f"error={type(exc).__name__}: {str(exc).splitlines()[0]},"
                f"proof={PROOF}")


def main():
    ref = read_values()
    strings = read_pairs(OUT / "locfit_verify5_r_strings.txt")
    r_ms = {k: float(v) for k, v in read_pairs(OUT / "locfit_verify5_r_timing.txt").items()}
    kdeb_names = strings["kdeb_names"].split("|")
    lines = []

    lines.append(run_case(
        "hatmatrix (reference t(locfit.raw geth=1) with ev=dat())", "hatmatrix_raw",
        lambda: hatmatrix_mod.hatmatrix(x=x, y=y),
        lambda out: out, ref["hatmatrix_raw"], r_ms["hatmatrix_raw"]))

    lines.append(run_case(
        "kappa0 (ev=dat())", "kappa0_dat",
        lambda: kappa0_mod.kappa0({"x": x, "y": y}, cov=0.95, ev=DATA_EV),
        lambda out: [out], ref["kappa0_dat"], r_ms["kappa0_dat"]))

    lines.append(run_case(
        "kdeb (no ev argument; data path)", "kdeb_dsamp",
        lambda: kdeb_mod.kdeb(dsamp),
        lambda out: [out[n] for n in kdeb_names], ref["kdeb_dsamp"], r_ms["kdeb_dsamp"]))

    lines.append(run_case(
        "lcv (ev=dat())", "lcv_dat",
        lambda: lcv_mod.lcv(x, y, ev=DATA_EV),
        lambda out: [out[k] for k in ("lik", "infl", "vari", "cv")],
        ref["lcv_dat"], r_ms["lcv_dat"]))

    lines.append(run_case(
        "lf (ev=dat())", "lf_dat",
        lambda: lf_mod.lf(x, y, alpha=0.5, deg=1, scale=2, kern="gauss",
                          maxk=50, ev=DATA_EV),
        lambda out: list(np.asarray(out["x"]).reshape(-1)) + [
            out["alpha"], out["deg"], out["scale"], out["maxk"]],
        np.concatenate([ref["lf_x"], ref["lf_num"]]), r_ms["lf_dat"],
        extra_ok=lambda out: (out["kern"] == strings["lf_kern"]
                              and out["ev"]["type"] == strings["lf_ev_type"]
                              and out["class"] == strings["lf_class"])))

    text = "\n".join(lines) + "\n"
    (OUT / "locfit_verify5_compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
