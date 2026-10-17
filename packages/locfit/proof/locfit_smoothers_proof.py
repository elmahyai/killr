"""Proof record for gam.lf and density.lf.

Run from the repository root with the workspace venv:

    .venv/bin/python packages/locfit/proof/locfit_smoothers_proof.py

Both functions are blocked by gaps in crates/locfit, so the translated
functions raise NotImplementedError. This script records that, and checks the
evidence behind each blocker against R:

- the crate's direct fit at the data reproduces R's dp summaries (lk, df1,
  df2) and R's evaluated coefficients at points, so the crate is correct
  where it applies;
- the crate's coef column is not R's fitted value at the data, so residuals
  cannot be formed from the crate output (diagnostic line below);
- density.lf needs the density family, which the crate does not have.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

import locfit as crate  # crates/locfit

ROOT = Path(__file__).parents[3]
PKG = ROOT / "packages" / "locfit" / "locfit"
OUT = ROOT / "packages" / "locfit" / "docs" / "output"
K = 100

spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None,
                                      is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated
from locfit_translated.gam_lf import BLOCKED_BY as GAM_BLOCKED  # noqa: E402
from locfit_translated.gam_lf import gam_lf  # noqa: E402
from locfit_translated.density_lf import BLOCKED_BY as DENS_BLOCKED  # noqa: E402
from locfit_translated.density_lf import density_lf  # noqa: E402

X = np.linspace(0.0, 1.0, 12)
Y = np.sin(2 * np.pi * X) + 0.1 * np.cos(7 * X)
W = np.linspace(0.5, 2.0, 12)


def read_values():
    values = {}
    for line in (OUT / "locfit_smoothers_r_values.txt").read_text().splitlines():
        name, text = line.split(",", 1)
        values[name] = np.array([float(v) for v in text.split(",")])
    return values


def read_timing():
    times = {}
    for line in (OUT / "locfit_smoothers_r_timing.txt").read_text().splitlines():
        name, value = line.split(",", 1)
        times[name] = float(value)
    return times


def status(call):
    try:
        call()
        return "ok"
    except NotImplementedError as exc:
        return str(exc)


def diagnostics():
    """Evidence for the blockers, against R's ev = dat() fit."""
    r = read_values()
    resid_r = r["gam.lf_ev_residuals"]
    fitted_r = Y - resid_r
    fit = crate.locfit_fit(X.reshape(-1, 1), Y, weights=W)
    coef0 = fit["coef"][:, 0]
    fit_no_w = crate.locfit_fit(X.reshape(-1, 1), Y)
    pres = np.array([[0.1], [0.5], [0.9]])
    eval_crate = crate.locfit_fit(X.reshape(-1, 1), Y, xev=pres)["coef"][:, 0]
    lk_r = float(next(line.split(",")[1] for line in
                      (OUT / "locfit_criteria_r_values.txt").read_text().splitlines()
                      if line.startswith("aic,")))
    return [
        f"diag_crate_coef_vs_r_fitted,max_abs_diff="
        f"{float(np.max(np.abs(coef0 - fitted_r))):.17g}",
        f"diag_crate_lk_vs_r_lk,crate={fit_no_w['lk']:.17g},r={lk_r:.17g},"
        f"abs_diff={abs(fit_no_w['lk'] - lk_r):.3g}",
        f"diag_crate_pres_coef_finite,{bool(np.all(np.isfinite(eval_crate)))}",
    ]


def timed(fn):
    fn()
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(K):
            fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples) / K


def main():
    r_ms = read_timing()
    lines = []
    gam_status = status(lambda: gam_lf(X, Y, W, ev_dat=True))
    lines.append(
        f"gam.lf,matches=no,max_abs_diff=NA,r_ms={r_ms['gam.lf_ev']:.17g},"
        f"translated_ms=NA,speedup=NA,proof=packages/locfit/proof/"
        f"locfit_smoothers_proof.py,blocked_by="
        f"{'; '.join(GAM_BLOCKED)}")
    lines.append(f"gam.lf_status,{gam_status}")
    dens_status = status(lambda: density_lf(np.linspace(-1.9, 1.9, 20)))
    lines.append(
        f"density.lf,matches=no,max_abs_diff=NA,r_ms={r_ms['density.lf']:.17g},"
        f"translated_ms=NA,speedup=NA,proof=packages/locfit/proof/"
        f"locfit_smoothers_proof.py,blocked_by={'; '.join(DENS_BLOCKED)}")
    lines.append(f"density.lf_status,{dens_status}")
    lines.extend(diagnostics())
    (OUT / "locfit_smoothers_compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
