"""Compare the fixed helper calls in requested_batch_r.R."""

from __future__ import annotations
import statistics
import time
import sys
import importlib.util
import importlib.machinery
from pathlib import Path
import numpy as np

PKG = Path(__file__).parents[1] / "locfit"
spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None,
                                      is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated
from locfit_translated.aic import aic
from locfit_translated.cp import cp
from locfit_translated.gcv import gcv
from locfit_translated.dat import dat
from locfit_translated.expit import expit
from locfit_translated.crit import crit
from locfit_translated.ang import ang
from locfit_translated.gam_lf import gam_lf
from locfit_translated.density_lf import density_lf

OUT = Path(__file__).parents[1] / "docs" / "output"
FIT = {"dp": {"lk": 1.25, "df1": 3.5, "df2": 4.25}, "mi": {"n": 20}}


def flat(v):
    if isinstance(v, str):
        return np.array([], dtype=float)
    if isinstance(v, dict):
        return np.concatenate([flat(x) for x in v.values()])
    return np.asarray(v, dtype=float).reshape(-1)


def main():
    ref = {}
    for line in (OUT / "locfit_requested_batch_r.txt").read_text().splitlines():
        if "," in line:
            key, values = line.split(",", 1)
            try:
                ref[key] = np.array([float(x) for x in values.split(",") if x])
            except ValueError:
                pass
    rtimes = {}
    for line in (OUT / "locfit_requested_batch_r_timing.txt").read_text().splitlines():
        name, value = line.split(",", 1)
        rtimes[name] = float(value)
    calls = {
        "dat": lambda: dat(),
        "expit": lambda: expit(np.array([-3., 0., 2.])),
        "aic": lambda: aic(FIT),
        "cp": lambda: cp(FIT, sig2=1),
        "gcv": lambda: gcv(FIT),
        "crit": lambda: crit().crit_val,
        "ang": lambda: ang(np.array([-1., 0., 1.])),
        "gam.lf": lambda: gam_lf(np.arange(1., 5.), np.array([1., 2., 1., 2.]))["residuals"],
        "density.lf": lambda: density_lf(np.array([0., 1., 2., 3.]), n=4, width=1, from_=0, to=3)["y"],
    }
    lines = []
    for name, call in calls.items():
        value = flat(call())
        expected = ref.get(name, np.array([]))
        diff = float(np.max(np.abs(value - expected))) if len(value) == len(expected) else float("inf")
        call()
        times = []
        for _ in range(20):
            start = time.perf_counter(); call()
            times.append((time.perf_counter() - start) * 1000)
        (OUT / f"locfit_{name.replace('.', '_')}_python.txt").write_text(
            "\n".join(f"{x:.17g}" for x in value) + "\n")
        translated_ms = statistics.median(times)
        r_ms = rtimes[name]
        lines.append(f"{name},matches={'yes' if diff <= 1e-8 else 'no'},"
                     f"max_abs_diff={diff:.17g},r_ms={r_ms:.9g},"
                     f"translated_ms={translated_ms:.9g},speedup={r_ms/translated_ms:.9g}")
    (OUT / "locfit_requested_batch_compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
