"""Proof: locfit.censor, locfit.quasi, locfit.robust and lscv on R's default ev = rbox().

R reference: rbox_default_r.R (locfit 1.5-9.12), written to
docs/output/locfit_default_ref. Each function is compared on the proof data
(d = 1, n = 150) and on a two-dimensional check (d = 2, n = 100):

- fitted values at the data (R fitted.locfit),
- standard errors at the data (R predict(se.fit = TRUE), band = "global"),
- the vertex table (R eva$coef: coef | nlx | t0 | lik | h, deg dropped),
- the vertices (R eva$xev),
- the summaries dp (lk, df1, df2, rv, rsc), and for lscv the criterion and df.

A case matches when every component agrees within 1e-8 and the shapes agree.
Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time.

Run from the repository root:
    /home/ahmed/killr_projects/killr/.venv/bin/python packages/locfit/proof/rbox_default_proof.py
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
from locfit_translated.locfit_quasi import locfit_quasi  # noqa: E402
from locfit_translated.locfit_robust import locfit_robust  # noqa: E402
from locfit_translated.lscv import lscv  # noqa: E402
from locfit_translated.locfit_raw import fitted, se_fit  # noqa: E402

PKG = L.PKG
REF = PKG / "docs" / "output" / "locfit_default_ref"
OUT = PKG / "docs" / "output"
PY_OUT = PKG / "docs" / "output" / "locfit_default_py"
TOL = 1e-8
PROOF = "packages/locfit/proof/rbox_default_proof.py"


def ref(name):
    return np.loadtxt(REF / f"{name}.csv", delimiter=",", ndmin=2)


def ref_vec(name):
    return ref(name).reshape(-1)


def r_timings():
    out = {}
    for line in (REF / "r_timing_default.csv").read_text().splitlines():
        key, value = line.split(",")
        out[key] = float(value)
    return out


def time_median_ms(fn):
    """One untimed call, then the median of 20 timed calls (perf_counter), in ms."""
    fn()
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def diff(a, b):
    a = np.asarray(a, dtype=float).reshape(-1)
    b = np.asarray(b, dtype=float).reshape(-1)
    if a.shape != b.shape:
        return float("inf")
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def components(name, fit, X_is_data=True):
    """Compare one fit against R's files for case ``name``. Returns (diffs, plain)."""
    eva = np.hstack([fit["coef"], fit["nlx"], fit["t0"], fit["lik"], fit["h"][:, None]])
    r_eva = ref(f"{name}_eva")
    r_eva = r_eva[:, :-1]  # R's last column is deg, not in the Python table
    dp = fit["dp"]
    r_dp = ref_vec(f"{name}_dp")
    diffs = {
        "fitted": diff(fitted(fit), ref_vec(f"{name}_fitted")),
        "se": diff(se_fit(fit), ref_vec(f"{name}_se")),
        "eva": diff(eva, r_eva) if eva.shape == r_eva.shape else float("inf"),
        "xev": diff(fit["xev"], ref_vec(f"{name}_xev")),
        "dp": diff([dp["lk"], dp["df1"], dp["df2"], dp["rv"], dp["rsc"]], r_dp),
    }
    return diffs, eva


def save(name, arrays):
    PY_OUT.mkdir(parents=True, exist_ok=True)
    for key, arr in arrays.items():
        a = np.asarray(arr, dtype=float)
        a = a.reshape(-1, 1) if a.ndim == 1 else a
        np.savetxt(PY_OUT / f"{name}_{key}.csv", a, delimiter=",", fmt="%.17g")


def main():
    d = L.inputs()
    x1, y1, cens1 = d["x1"], d["y1"], d["cens1"]
    x2, y2 = d["x2"], d["y2"]
    dsamp = d["dsamp"]
    cens2 = (x2[:, 0] > 0.85).astype(float)
    kw = dict(alpha=0.7, deg=2, kern="tricube", kt="sph")

    cases = {
        "censor_d1": (lambda: locfit_censor(x1, y1, cens=cens1, **kw), "locfit.censor"),
        "quasi_d1": (lambda: locfit_quasi(x1, y1, **kw), "locfit.quasi"),
        "robust_d1": (lambda: locfit_robust(x1, y1, **kw), "locfit.robust"),
        "censor_d2": (lambda: locfit_censor(x2, y2, cens=cens2, **kw), "locfit.censor (d = 2)"),
        "quasi_d2": (lambda: locfit_quasi(x2, y2, **kw), "locfit.quasi (d = 2)"),
        "robust_d2": (lambda: locfit_robust(x2, y2, **kw), "locfit.robust (d = 2)"),
    }
    rt = r_timings()
    rows = []
    detail = []
    results = {}
    for name, (fn, label) in cases.items():
        fit = fn()
        diffs, eva = components(name, fit)
        worst = max(diffs.values())
        matches = worst <= TOL
        t_ms = time_median_ms(fn)
        r_ms = rt[name]
        results[name] = (matches, worst, r_ms, t_ms)
        rows.append(
            f"{label},matches={'yes' if matches else 'no'},max_abs_diff={worst:.3e},"
            f"r_ms={r_ms:.6g},translated_ms={t_ms:.6g},speedup={r_ms / t_ms:.4g},"
            f"proof={PROOF},python=locfit.locfit_{name.split('_')[0]}.locfit_{name.split('_')[0]}"
        )
        detail.append(f"case={name} vertices={eva.shape[0]} "
                      + " ".join(f"{k}={v:.3e}" for k, v in diffs.items()))
        save(name, {"fitted": fitted(fit), "se": se_fit(fit), "eva": eva, "xev": fit["xev"]})
        print(rows[-1])
        print(detail[-1])

    lf = lscv(dsamp)
    r_lscv = ref_vec("lscv_default")
    dl = diff(lf, r_lscv)
    t_lscv = time_median_ms(lambda: lscv(dsamp))
    matches = dl <= TOL
    rows.append(
        f"lscv,matches={'yes' if matches else 'no'},max_abs_diff={dl:.3e},"
        f"r_ms={rt['lscv']:.6g},translated_ms={t_lscv:.6g},speedup={rt['lscv'] / t_lscv:.4g},"
        f"proof={PROOF},python=locfit.lscv.lscv"
    )
    detail.append(f"case=lscv_default criterion_df diff={dl:.3e}")
    PY_OUT.mkdir(parents=True, exist_ok=True)
    np.savetxt(PY_OUT / "lscv_default.csv", np.asarray(lf, dtype=float).reshape(-1, 1),
               delimiter=",", fmt="%.17g")
    print(rows[-1])
    print(detail[-1])

    text = "\n".join(rows) + "\n" + "\n".join(detail) + "\n"
    (OUT / "locfit_default_compare.txt").write_text(text)
    ok = all(v[0] for k, v in results.items() if k.endswith("d1")) and matches
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
