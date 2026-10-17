"""Proof: lf() on R's default ev = rbox() (adaptive kd-tree spec), d = 1 and d = 2.

R reference: lf-default-r.R (locfit 1.5-9.12), written to docs/output/lf_default_r.
The fixed inputs are read from the same files, so R and Python see the same
numbers. This script never calls R.

Each term case compares with R within 1e-8: the covariate matrix (lf's
cbind(...)), alpha, deg, scale, maxk, and the numeric fields of the default
ev (xev, mg, cut, ll, ur). The ev type string is compared exactly. The explicit
ev = dat() cases compare the matrix, the four scalars and the ev type (the
Python ev dict {"type": "data"} has no numeric fields).

Chain cases: the lf default ev is passed to locfit_raw (the crate kernel's tree
path, crates/locfit fit_tree), and the fitted values are compared with R's
locfit.raw on the same ev.

Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time (R: Sys.time()).

Run from the repository root:
    .venv/bin/python packages/locfit/proof/lf-default-py.py
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.locfit_raw import fitted, locfit_raw  # noqa: E402

# lf.py has no relative imports; load it by path as the other proofs do.
_spec = importlib.util.spec_from_file_location("locfit_lf_default", L.PKG / "locfit" / "lf.py")
_lf_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lf_mod)
lf = _lf_mod.lf

PKG = L.PKG
REF = PKG / "docs" / "output" / "lf_default_r"
OUT = PKG / "docs" / "output"
TOL = 1e-8
PROOF = "packages/locfit/proof/lf-default-py.py"


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


def r_type(name):
    return (REF / f"{name}_ev_type.txt").read_text().strip()


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


def ev_numeric(ev):
    """The numeric fields of the Python ev dict, in R's order (xev, mg, cut, ll, ur)."""
    return np.concatenate([[ev["xev"], ev["mg"], ev["cut"]],
                           np.asarray(ev["ll"], dtype=float),
                           np.asarray(ev["ur"], dtype=float)])


def term_case(name, fn, default):
    """Compare one lf() term with R. Returns (diffs, type_ok, term)."""
    term = fn()
    diffs = {
        "x": diff(term["x"], rd(f"{name}_x")),
        "num": diff([term["alpha"], term["deg"], term["scale"], term["maxk"]],
                    rv(f"{name}_num")),
    }
    if default:
        diffs["ev"] = diff(ev_numeric(term["ev"]), rv(f"{name}_ev"))
    type_ok = term["ev"]["type"] == r_type(name)
    return diffs, type_ok, term


def main():
    x1 = rd("in_x1").reshape(-1, 1)
    y1 = rv("in_y1")
    x2 = rd("in_x2")
    y2 = rv("in_y2")

    rt = r_timings()
    rows = []
    detail = []
    ok = True

    def emit(label, case, diffs, type_ok, r_ms, t_ms, python):
        nonlocal ok
        worst = max(diffs.values())
        matches = type_ok and worst <= TOL
        ok = ok and matches
        rows.append(
            f"{label},case={case},matches={'yes' if matches else 'no'},"
            f"max_abs_diff={worst:.3e},r_ms={r_ms:.6g},translated_ms={t_ms:.6g},"
            f"speedup={r_ms / t_ms:.4g},proof={PROOF},python={python}")
        detail.append(f"case={case} type_ok={type_ok} "
                      + " ".join(f"{k}={v:.3e}" for k, v in diffs.items()))
        print(rows[-1])
        print(detail[-1])

    # lf() term cases, d = 1 (one covariate) and d = 2 (two covariates).
    term_specs = [
        ("lf_d1", lambda: lf(x1[:, 0]), True),
        ("lf_d2", lambda: lf(x2[:, 0], x2[:, 1]), True),
        ("lf_d1_dat", lambda: lf(x1[:, 0], alpha=0.5, deg=1, scale=2, kern="gauss",
                                 maxk=50, ev={"type": "data"}), False),
        ("lf_d2_dat", lambda: lf(x2[:, 0], x2[:, 1], alpha=0.5, deg=1, scale=2,
                                 kern="gauss", maxk=50, ev={"type": "data"}), False),
    ]
    for name, fn, default in term_specs:
        diffs, type_ok, _ = term_case(name, fn, default)
        t_ms = time_median_ms(fn)
        emit("lf", name, diffs, type_ok, rt[name], t_ms,
             "locfit.lf.lf (smooth term, ev default rbox tree)" if default
             else "locfit.lf.lf (smooth term, ev dat)")

    # Chain cases: lf default ev -> crate tree fit, compared with R locfit.raw on rbox().
    chain_specs = [
        ("chain_d1", x1, y1, lambda: lf(x1[:, 0])),
        ("chain_d2", x2, y2, lambda: lf(x2[:, 0], x2[:, 1])),
    ]
    for name, x, y, term in chain_specs:
        def chain(x=x, y=y, term=term):
            return locfit_raw(x, y, ev=term()["ev"])
        fit = chain()
        diffs = {"fitted": diff(fitted(fit), rv(f"{name}_fitted"))}
        t_ms = time_median_ms(chain)
        emit("lf chain", name, diffs, True, rt[name], t_ms,
             "locfit.lf.lf ev -> locfit.locfit_raw.locfit_raw (crate tree)")

    text = "\n".join(rows) + "\n" + "\n".join(detail) + "\n"
    (OUT / "lf_default_compare.txt").write_text(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
