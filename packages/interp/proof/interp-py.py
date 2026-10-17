"""Proof: interp.interp.interp against R interp 1.1-6 interp on the default path and common options.

Run after proof/interp-r.R, from packages/interp:
    Rscript proof/interp-r.R && python3 proof/interp-py.py
Grid values are compared in R's column-major order. NaN is R's NA.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

from interp_proof_common import compare, lcg, median_ms, read_record, report, write_record  # noqa: E402
from interp.interp import interp  # noqa: E402


def f(x, y):
    return np.sin(2 * x) + np.cos(3 * y)


s60 = lcg(120, 42)
s200 = lcg(400, 7)
s30 = lcg(60, 5)
s80 = lcg(80, 99)
x30 = s30[0:30]
y30 = s30[30:60]
dupi = np.array([1, 6, 10])  # R indices 2, 7, 11
xdup = np.concatenate([x30, x30[dupi]])
ydup = np.concatenate([y30, y30[dupi]])
zdup = f(xdup, ydup) + 0.1 * np.arange(1, len(xdup) + 1)

rq = lcg(300, 1234)
x200 = s200[0:200]
y200 = s200[200:400]
pts_x = x200.min() - 0.2 + (x200.max() - x200.min() + 0.4) * rq[0:150]
pts_y = y200.min() - 0.2 + (y200.max() - y200.min() + 0.4) * rq[150:300]

gx = np.linspace(0, 1, 6)
gy = np.linspace(0, 2, 5)
zgrid = np.sin(3 * gx)[:, None] + (gy ** 2)[None, :]

x60 = s60[0:60]
y60 = s60[60:120]
xs = s80[0:40] * 100 - 50
ys = s80[40:80]

# (id, call arguments), in the same order as proof/interp-r.R.
CASES = [
    ("rand60", dict(x=x60, y=y60, z=f(x60, y60))),
    ("rand200", dict(x=x200, y=y200, z=f(x200, y200))),
    (
        "grid5",
        dict(
            x=np.tile(np.arange(1.0, 6.0), 5),
            y=np.repeat(np.arange(1.0, 6.0), 5),
            z=np.tile(np.arange(1.0, 6.0), 5) * np.repeat(np.arange(1.0, 6.0), 5) + np.tile(np.arange(1.0, 6.0), 5),
        ),
    ),
    ("scaled", dict(x=xs, y=ys, z=f(xs, ys))),
    ("dups-mean", dict(x=xdup, y=ydup, z=zdup, duplicate="mean")),
    ("dups-median", dict(x=xdup, y=ydup, z=zdup, duplicate="median")),
    ("dups-strip", dict(x=xdup, y=ydup, z=zdup, duplicate="strip")),
    ("dups-user", dict(x=xdup, y=ydup, z=zdup, duplicate="user", dupfun=lambda v: np.max(v))),
    ("grid-input", dict(x=gx, y=gy, z=zgrid, input="grid")),
    ("points-out", dict(x=x200, y=y200, z=f(x200, y200), xo=pts_x, yo=pts_y, output="points")),
    (
        "custom-grid",
        dict(x=x60, y=y60, z=f(x60, y60), xo=np.linspace(0.1, 0.9, 25), yo=np.linspace(0.05, 0.95, 31)),
    ),
    ("akima-lin", dict(x=x60, y=y60, z=f(x60, y60), method="akima", linear=True)),
    ("extrap-on", dict(x=x60, y=y60, z=f(x60, y60), extrap=True)),
]


def run_case(kw):
    return interp(rng=np.random.default_rng(0), **kw)


def run_all():
    return [run_case(kw) for _, kw in CASES]


def records(res):
    rec = {}
    for (cid, _), r in zip(CASES, res):
        rec[f"{cid}/xo"] = np.asarray(r["x"], dtype=float)
        rec[f"{cid}/yo"] = np.asarray(r["y"], dtype=float)
        # Column-major, as R's as.vector on the matrix.
        rec[f"{cid}/z"] = np.asarray(r["z"], dtype=float).ravel(order="F")
    return rec


if __name__ == "__main__":
    res = run_all()  # one untimed call, used for the records
    rec = records(res)
    py_ms = median_ms(run_all, reps=20)
    write_record("interp", rec, py_ms)

    r_rec = read_record("interp")
    py_rec = {k: np.asarray(v, dtype=float).ravel() for k, v in rec.items()}
    ok, max_diff, bad = compare(py_rec, r_rec)
    na_cells = int(sum(np.sum(np.isnan(np.asarray(r["z"], dtype=float))) for r in res))
    report(
        "interp",
        ok,
        max_diff,
        r_rec["_r_median_ms"][0],
        py_ms,
        extra={
            "cases": len(CASES),
            "na_cells": na_cells,
            "compared_keys": len([k for k in r_rec if not k.startswith("_")]),
            "mismatched_keys": bad if bad else "none",
        },
    )
