"""Proof: locfit.censor() on R's default ev = rbox() (adaptive kd-tree).

R reference: locfit-censor-default-r.R (locfit 1.5-9.12), written to
docs/output/locfit_censor_default_r. The fixed inputs (x, y, cens) are read from
those files. This script never calls R.

Each case (d = 1 and d = 2) compares with R within 1e-8:
- fitted values at the data (R fitted.locfit),
- the vertex table (R eva$coef without the trailing deg column),
- the vertices (R eva$xev),
- the summaries dp (lk, df1, df2, rv, rsc).

Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time (R: Sys.time()).

Run from the repository root:
    .venv/bin/python packages/locfit/proof/locfit-censor-default-py.py
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
from locfit_translated.locfit_censor import locfit_censor  # noqa: E402
from locfit_translated.locfit_raw import fitted  # noqa: E402

PKG = L.PKG
IN = PKG / "docs" / "output" / "locfit_default_r"
REF = PKG / "docs" / "output" / "locfit_censor_default_r"
OUT = PKG / "docs" / "output"
PY_OUT = OUT / "locfit_censor_default_py"
TOL = 1e-8
PROOF = "packages/locfit/proof/locfit-censor-default-py.py"


def rd(path):
    return np.loadtxt(path, delimiter=",", ndmin=2)


def rv(path):
    return rd(path).reshape(-1)


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
    dp = fit["dp"]
    diffs = {
        "fitted": diff(fitted(fit), rv(REF / f"{name}_fitted.csv")),
        "eva": diff(eva, rd(REF / f"{name}_eva.csv")),
        "xev": diff(np.asarray(fit["xev"]).reshape(-1), rv(REF / f"{name}_xev.csv")),
        "dp": diff([dp["lk"], dp["df1"], dp["df2"], dp["rv"], dp["rsc"]],
                   rv(REF / f"{name}_dp.csv")),
    }
    return diffs, eva


def save(name, fit):
    PY_OUT.mkdir(parents=True, exist_ok=True)
    eva = np.hstack([fit["coef"], fit["nlx"], fit["t0"], fit["lik"], fit["h"][:, None]])
    np.savetxt(PY_OUT / f"{name}_fitted.csv", np.asarray(fitted(fit)).reshape(-1, 1),
               delimiter=",", fmt="%.17g")
    np.savetxt(PY_OUT / f"{name}_eva.csv", eva, delimiter=",", fmt="%.17g")


def main():
    x1 = rd(IN / "in_x1.csv").reshape(-1, 1)
    y1 = rv(IN / "in_y1.csv")
    x2 = rd(IN / "in_x2.csv")
    y2 = rv(IN / "in_y2.csv")
    c1 = rv(REF / "in_cens1.csv")
    c2 = rv(REF / "in_cens2.csv")
    cases = {
        "censor_d1": (x1, y1, c1),
        "censor_d2": (x2, y2, c2),
    }
    rt = r_timings()
    rows = []
    detail = []
    ok = True
    for name, (x, y, c) in cases.items():
        fit = locfit_censor(x, y, cens=c)
        diffs, eva = components(name, fit)
        worst = max(diffs.values())
        matches = worst <= TOL
        ok = ok and matches
        t_ms = time_median_ms(lambda: locfit_censor(x, y, cens=c))
        r_ms = rt[name]
        d = x.shape[1]
        rows.append(
            f"locfit.censor (d = {d}),matches={'yes' if matches else 'no'},"
            f"max_abs_diff={worst:.3e},r_ms={r_ms:.6g},translated_ms={t_ms:.6g},"
            f"speedup={r_ms / t_ms:.4g},proof={PROOF},python=locfit.locfit_censor.locfit_censor"
        )
        detail.append(f"case={name} vertices={eva.shape[0]} "
                      + " ".join(f"{k}={v:.3e}" for k, v in diffs.items()))
        save(name, fit)
        print(rows[-1])
        print(detail[-1])

    text = "\n".join(rows) + "\n" + "\n".join(detail) + "\n"
    (OUT / "locfit_censor_default_compare.txt").write_text(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
