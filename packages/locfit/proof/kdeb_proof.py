"""Proof for kdeb: R locfit 1.5-9.12 bandwidth selection (.C("kdeb")) against
the Python port in packages/locfit/locfit/kdeb.py (crates/locfit kdeb).

Run from the repository root with the workspace venv (it has the crate):

    .venv/bin/python packages/locfit/proof/kdeb_proof.py

R's values and timings come from kdeb_r.R, on the fixed samples written by
kernel_inputs_r.R. Each case is one kdeb call with the same arguments in R and
Python. A case matches when every bandwidth is within 1e-8 of R and the method
names agree.

Timing: one untimed call, then the median of 20 timed calls (each call is
timed on its own with time.perf_counter()). speedup = r_ms / translated_ms.
"""

from __future__ import annotations

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
PROOF = "packages/locfit/proof/kdeb_proof.py"

spec = importlib.util.spec_from_file_location("locfit_kdeb", PKG / "locfit" / "kdeb.py")
kdeb_mod = importlib.util.module_from_spec(spec)
sys.modules["locfit_kdeb"] = kdeb_mod
spec.loader.exec_module(kdeb_mod)
kdeb = kdeb_mod.kdeb

dsamp = np.genfromtxt(OUT / "locfit_kernel_dsamp.csv", delimiter=",", names=True)["dsamp"]
xin = np.genfromtxt(OUT / "locfit_kernel_inputs.csv", delimiter=",", names=True)["x"]

CALLS = {
    "dsamp_default": (dsamp, {}),
    "inputs_x_default": (xin, {}),
    "dsamp_h0h1": (dsamp, {"h0": 0.05, "h1": 0.8, "meth": ("SJPI", "AIC", "GKK")}),
    "dsamp_meth_subset": (dsamp, {"meth": ("LSCV", "BCV")}),
}


def read_r_values():
    vals = {}
    for line in (OUT / "locfit_kdeb_r_values.txt").read_text().splitlines():
        case, names, text = line.split(",", 2)
        vals[case] = (names.split("|"), np.array([float(v) for v in text.split(",")]))
    return vals


def read_r_timing():
    return {k: float(v) for k, v in
            (line.split(",") for line in (OUT / "locfit_kdeb_r_timing.txt").read_text().splitlines())}


def timed_ms(fn):
    fn()  # one untimed call
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def main():
    ref = read_r_values()
    r_ms = read_r_timing()
    lines = []
    py_lines = []
    for case, (x, kw) in CALLS.items():
        names, want = ref[case]
        call = lambda x=x, kw=kw: kdeb(x, **kw)
        out = call()
        got_names = list(out.keys())
        got = np.array([out[n] for n in names], dtype=float)
        diff = float(np.max(np.abs(got - want))) if got_names == names else float("inf")
        matches = "yes" if diff <= TOL else "no"
        py_ms = timed_ms(call)
        lines.append(
            f"kdeb,case={case},matches={matches},max_abs_diff={diff:.3e},"
            f"r_ms={r_ms[case]:.6g},translated_ms={py_ms:.6g},"
            f"speedup={r_ms[case] / py_ms:.6g},proof={PROOF}")
        py_lines.append(f"{case},{'|'.join(names)},"
                        + ",".join(f"{v:.17g}" for v in got))
    text = "\n".join(lines) + "\n"
    (OUT / "locfit_kdeb_compare.txt").write_text(text)
    (OUT / "locfit_kdeb_python_values.txt").write_text("\n".join(py_lines) + "\n")
    print(text, end="")


if __name__ == "__main__":
    main()
