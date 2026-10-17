"""Proof: interp.on_convex_hull.on_convex_hull against R interp 1.1-6 on.convex.hull.

Run after proof/on.convex.hull-r.R, from packages/interp:
    Rscript proof/on.convex.hull-r.R && python3 proof/on.convex.hull-py.py
The queries are rebuilt here from the same Park-Miller points and the same
lattice, so the inputs match R exactly.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

from interp_proof_common import compare, lcg, median_ms, point_cases, read_record, report, write_record  # noqa: E402
from interp.tri_mesh import tri_mesh  # noqa: E402
from interp.on_convex_hull import on_convex_hull  # noqa: E402

KEEP = {"rand60", "grid5", "scaled40", "quad4", "dups-remove"}
CASES = [c for c in point_cases() if c["id"] in KEEP]


def make_queries(c):
    x, y = c["x"], c["y"]
    lo_x = x.min() - 0.5
    hi_x = x.max() + 0.5
    lo_y = y.min() - 0.5
    hi_y = y.max() + 0.5
    k = np.arange(12)
    lat_x = lo_x + (hi_x - lo_x) * k / 11
    lat_y = lo_y + (hi_y - lo_y) * k / 11
    rnd = lcg(80, 1234)
    qx = np.concatenate([x, np.tile(lat_x, 12), lo_x + (hi_x - lo_x) * rnd[0:40]])
    qy = np.concatenate([y, np.repeat(lat_y, 12), lo_y + (hi_y - lo_y) * rnd[40:80]])
    return qx, qy


TRIS = [tri_mesh(c["x"], c["y"], duplicate=c["dup"]) for c in CASES]
QS = [make_queries(c) for c in CASES]


def run_all():
    return [on_convex_hull(t, qx, qy) for t, (qx, qy) in zip(TRIS, QS)]


def run_eps():
    return [on_convex_hull(t, qx, qy, eps=1e-3) for t, (qx, qy) in zip(TRIS, QS)]


def records(res, res_eps):
    rec = {}
    for c, (qx, qy), r, re in zip(CASES, QS, res, res_eps):
        cid = c["id"]
        rec[f"{cid}/query_x"] = qx
        rec[f"{cid}/query_y"] = qy
        rec[f"{cid}/on"] = r.astype(float)
        rec[f"{cid}/on_eps1e-3"] = re.astype(float)
    return rec


if __name__ == "__main__":
    res = run_all()  # one untimed call, used for the records
    res_eps = run_eps()
    rec = records(res, res_eps)
    py_ms = median_ms(run_all, reps=20)
    write_record("on.convex.hull", rec, py_ms)

    r_rec = read_record("on.convex.hull")
    py_rec = {k: np.asarray(v, dtype=float).ravel() for k, v in rec.items()}
    ok, max_diff, bad = compare(py_rec, r_rec)
    n_on = int(sum(np.sum(r) for r in res))
    report(
        "on.convex.hull",
        ok,
        max_diff,
        r_rec["_r_median_ms"][0],
        py_ms,
        extra={
            "cases": len(CASES),
            "queries_on_hull_default_eps": n_on,
            "compared_keys": len([k for k in r_rec if not k.startswith("_")]),
            "mismatched_keys": bad if bad else "none",
        },
    )
