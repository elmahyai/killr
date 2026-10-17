"""Proof: locfit(), locfit.raw() on R's default ev = rbox() (adaptive kd-tree).

R reference: locfit-default-r.R (locfit 1.5-9.12), written to
docs/output/locfit_default_r. The fixed inputs are read from the same files, so
the R and Python sides see the same numbers. This script never calls R.

Each case compares every component with R within 1e-8:
- fitted values at the data (R fitted.locfit),
- standard errors at the data (R predict(se.fit = TRUE)),
- the vertex table (R eva$coef without the trailing deg column),
- the vertices (R eva$xev),
- the summaries dp (lk, df1, df2, rv, rsc).

Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time (R: Sys.time()).

Run from the repository root:
    .venv/bin/python packages/locfit/proof/locfit-default-py.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.locfit import locfit  # noqa: E402
from locfit_translated.locfit_raw import fitted, locfit_raw, se_fit  # noqa: E402

PKG = L.PKG
REF = PKG / "docs" / "output" / "locfit_default_r"
OUT = PKG / "docs" / "output"
PY_OUT = OUT / "locfit_default_py"
TOL = 1e-8
PROOF = "packages/locfit/proof/locfit-default-py.py"


def rd(name):
    return np.loadtxt(REF / f"{name}.csv", delimiter=",", ndmin=2)


def rv(name):
    return rd(name).reshape(-1)


def r_timings():
    out = {}
    for line in (REF / "timing.csv").read_text().splitlines():
        key, value = line.split(",")
        out[key] = float(value)
    return out


def diff(a, b):
    a = np.asarray(a, dtype=float).reshape(-1)
    b = np.asarray(b, dtype=float).reshape(-1)
    if a.shape != b.shape:
        return float("inf")
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def time_median_ms(fn):
    """One untimed call, then the median of 20 timed calls (perf_counter), in ms."""
    fn()
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def components(name, fit):
    eva = np.hstack([fit["coef"], fit["nlx"], fit["t0"], fit["lik"], fit["h"][:, None]])
    r_eva = rd(f"{name}_eva")
    dp = fit["dp"]
    dp_vec = [dp["lk"], dp["df1"], dp["df2"], dp["rv"], dp["rsc"]]
    return {
        "fitted": diff(fitted(fit), rv(f"{name}_fitted")),
        "se": diff(se_fit(fit), rv(f"{name}_se")),
        "eva": diff(eva, r_eva) if eva.shape == r_eva.shape else float("inf"),
        "xev": diff(fit["xev"], rv(f"{name}_xev")),
        "dp": diff(dp_vec, rv(f"{name}_dp")),
    }, eva


def save(name, arrays):
    PY_OUT.mkdir(parents=True, exist_ok=True)
    for key, arr in arrays.items():
        a = np.asarray(arr, dtype=float)
        a = a.reshape(-1, 1) if a.ndim == 1 else a
        np.savetxt(PY_OUT / f"{name}_{key}.csv", a, delimiter=",", fmt="%.17g")


def main():
    x1 = rd("in_x1").reshape(-1, 1)
    y1 = rv("in_y1")
    x2 = rd("in_x2")
    y2 = rv("in_y2")
    d1 = {"x": x1[:, 0], "y": y1}
    d2 = {"x1": x2[:, 0], "x2": x2[:, 1], "y": y2}

    cases = {
        "locfit_d1": (lambda: locfit("y ~ x", d1), "locfit (d = 1)"),
        "locfit_d2": (lambda: locfit("y ~ x1 + x2", d2), "locfit (d = 2)"),
        "locfit.raw_d1": (lambda: locfit_raw(x1, y1), "locfit.raw (d = 1)"),
        "locfit.raw_d2": (lambda: locfit_raw(x2, y2), "locfit.raw (d = 2)"),
    }
    rt = r_timings()
    rows = []
    detail = []
    ok = True
    for name, (fn, label) in cases.items():
        fit = fn()
        diffs, eva = components(name, fit)
        worst = max(diffs.values())
        matches = worst <= TOL
        ok = ok and matches
        t_ms = time_median_ms(fn)
        r_ms = rt[name]
        rows.append(
            f"{label},matches={'yes' if matches else 'no'},max_abs_diff={worst:.3e},"
            f"r_ms={r_ms:.6g},translated_ms={t_ms:.6g},speedup={r_ms / t_ms:.4g},"
            f"proof={PROOF},python={'locfit.locfit.locfit' if name.startswith('locfit_') else 'locfit.locfit_raw.locfit_raw'}"
        )
        detail.append(f"case={name} vertices={eva.shape[0]} "
                      + " ".join(f"{k}={v:.3e}" for k, v in diffs.items()))
        save(name, {"fitted": fitted(fit), "se": se_fit(fit), "eva": eva, "xev": fit["xev"]})
        print(rows[-1])
        print(detail[-1])

    text = "\n".join(rows) + "\n" + "\n".join(detail) + "\n"
    (OUT / "locfit_default_path_compare.txt").write_text(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
