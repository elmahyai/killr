"""Proof and timing for crit() at d = 2 against R (locfit 1.5-9.12).

Run from the repository root with the workspace venv (it has the locfit
crate, which supplies scritval):

    .venv/bin/python packages/locfit/proof/crit-d2-py.py

The R values come from crit-d2-r.R. The timed call is the translated crit()
with d = 2, which calls the crate's scritval. One untimed call, then the median
of 20 timed single calls, measured with time.perf_counter().
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[3]
PKG = ROOT / "packages" / "locfit" / "locfit"
OUT = ROOT / "packages" / "locfit" / "docs" / "output"
TOL = 1e-8

# Load the translated package as a namespace so its relative imports resolve.
spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None,
                                      is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated
from locfit_translated.crit import crit  # noqa: E402

# Same const, d, and cov as crit-d2-r.R. The fixed-fit case uses the
# critical-value object of the R fit locfit(y ~ x1 + x2), whose const is
# c(0, 0, 1) and d = 2 (printed by crit-d2-r.R).
CASES = {
    "d2_c01_cov095": dict(const=(0.0, 1.0), d=2, cov=0.95),
    "d2_c01_cov090": dict(const=(0.0, 1.0), d=2, cov=0.90),
    "d2_c001_cov095": dict(const=(0.0, 0.0, 1.0), d=2, cov=0.95),
    "d2_c021_cov095": dict(const=(0.2, 0.5, 1.0), d=2, cov=0.95),
}
FIT_CASE = "fit2_critval"
FIT_ARGS = dict(const=(0.0, 0.0, 1.0), d=2, cov=0.95)


def read_pairs(path):
    return {k: float(v) for k, v in
            (line.split(",", 1) for line in path.read_text().splitlines() if line)}


def median_ms(f):
    f()  # untimed call
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        f()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def main():
    ref = read_pairs(OUT / "crit-d2-r_values.txt")
    r_ms = read_pairs(OUT / "crit-d2-r_timing.txt")

    values = {name: crit(**args).crit_val for name, args in CASES.items()}
    values[FIT_CASE] = crit(**FIT_ARGS).crit_val
    (OUT / "crit-d2-py_values.txt").write_text(
        "".join(f"{k},{v!r}\n" for k, v in values.items()))

    lines = []
    for name in CASES:
        diff = abs(values[name] - ref[name])
        py_ms = median_ms(lambda a=CASES[name]: crit(**a).crit_val)
        lines.append(
            f"crit d=2 {name},matches={'yes' if diff <= TOL else 'no'},"
            f"max_abs_diff={diff:.3e},r_ms={r_ms[name]:.6g},"
            f"translated_ms={py_ms:.6g},speedup={r_ms[name] / py_ms:.6g},"
            f"proof=packages/locfit/proof/crit-d2-py.py")
    diff = abs(values[FIT_CASE] - ref[FIT_CASE])
    lines.append(
        f"crit d=2 fixed fit (fit$critval),matches={'yes' if diff <= TOL else 'no'},"
        f"max_abs_diff={diff:.3e},r_ms=not timed,translated_ms=not timed,"
        f"speedup=not timed,proof=packages/locfit/proof/crit-d2-py.py")
    text = "\n".join(lines) + "\n"
    (OUT / "crit-d2-compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
