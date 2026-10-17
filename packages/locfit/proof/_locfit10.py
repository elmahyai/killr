"""Shared helpers for the locfit proofs in this folder.

The R reference and the fixed inputs come from locfit10_r.R (docs/output/locfit_ref).
A proof runs the translated function, compares every output with max absolute
difference <= 1e-8, and times both sides: one untimed call, then the median of
20 samples, each a loop of 20 calls, with time.perf_counter(). R's time is the
same protocol with Sys.time().
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
PKG = PROOF.parent
REF = PKG / "docs" / "output" / "locfit_ref"
PY_OUT = PKG / "docs" / "output" / "locfit_py"
TOL = 1e-8


def load_translated():
    """Import packages/locfit as the package locfit_translated (sys.path is unchanged)."""
    if "locfit_translated" not in sys.modules:
        spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None, is_package=True)
        spec.submodule_search_locations = [str(PKG)]
        mod = importlib.util.module_from_spec(spec)
        sys.modules["locfit_translated"] = mod
    return sys.modules["locfit_translated"]


def ref(name):
    return np.loadtxt(REF / f"{name}.csv", delimiter=",", ndmin=2)


def ref_vec(name):
    return ref(name).reshape(-1)


def inputs():
    return {
        "x1": ref("in_x1"), "y1": ref_vec("in_y1"), "w1": ref_vec("in_w1"),
        "b1": ref_vec("in_b1"), "cens1": ref_vec("in_cens1"), "x2": ref("in_x2"),
        "y2": ref_vec("in_y2"), "xev1": ref_vec("in_xev1"), "dsamp": ref_vec("in_dsamp"),
        "xa": ref_vec("in_xa"), "xb": ref_vec("in_xb"),
    }


def r_timing(name):
    for line in (REF / "r_timing.csv").read_text().splitlines():
        key, value = line.split(",")
        if key == name:
            return float(value)
    raise KeyError(name)


def timed_ms(fn, samples=20, loops=20):
    """Median ms per call: one untimed call, then `samples` loops of `loops` calls."""
    fn()
    times = []
    for _ in range(samples):
        t0 = time.perf_counter()
        for _ in range(loops):
            fn()
        times.append((time.perf_counter() - t0) * 1000.0 / loops)
    return statistics.median(times)


def max_diff(got, want):
    g = np.asarray(got, dtype=float).reshape(-1)
    w = np.asarray(want, dtype=float).reshape(-1)
    if g.shape != w.shape:
        return float("inf")
    return float(np.max(np.abs(g - w))) if g.size else 0.0


def save(name, arr):
    a = np.asarray(arr, dtype=float)
    a = a.reshape(-1, 1) if a.ndim == 1 else a.reshape(1, 1) if a.ndim == 0 else a
    PY_OUT.mkdir(parents=True, exist_ok=True)
    np.savetxt(PY_OUT / f"{name}.csv", a, delimiter=",", fmt="%.17g")


def finish(fn, diffs, translated_ms):
    """Write and print one comparison: matches, max_abs_diff, r_ms, translated_ms, speedup."""
    worst = max(diffs.values())
    matches = worst <= TOL
    r_ms = r_timing(fn)
    line = (f"{fn},matches={'yes' if matches else 'no'},max_abs_diff={worst:.3e},"
            f"r_ms={r_ms:.6g},translated_ms={translated_ms:.6g},"
            f"speedup={r_ms / translated_ms:.6g}")
    detail = "\n".join(f"  {k}: max_abs_diff={v:.3e}" for k, v in diffs.items())
    text = f"{line}\n{detail}\n"
    PY_OUT.mkdir(parents=True, exist_ok=True)
    (PY_OUT / f"locfit_{fn}_compare.txt").write_text(text)
    print(text, end="")
    return matches


def blocked(fn, reason):
    """Record a function the kernel cannot run. No comparison is claimed."""
    r_ms = r_timing(fn)
    line = (f"{fn},matches=no,max_abs_diff=NA,r_ms={r_ms:.6g},translated_ms=NA,"
            f"speedup=NA,blocked_by={reason}")
    PY_OUT.mkdir(parents=True, exist_ok=True)
    (PY_OUT / f"locfit_{fn}_compare.txt").write_text(line + "\n")
    print(line)
