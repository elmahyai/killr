"""Proof: interp.tri_find.tri_find against R interp 1.1-6 tri.find.

Run after proof/tri.find-r.R, from packages/interp:
    Rscript proof/tri.find-r.R && python3 proof/tri.find-py.py
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
from interp.tri_find import tri_find  # noqa: E402

KEEP = {"rand60", "rand200", "grid5", "scaled40", "dups-remove", "quad4"}
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
    return [tri_find(t, qx, qy) for t, (qx, qy) in zip(TRIS, QS)]


def records(res):
    rec = {}
    for c, (qx, qy), r in zip(CASES, QS, res):
        cid = c["id"]
        rec[f"{cid}/query_x"] = qx
        rec[f"{cid}/query_y"] = qy
        rec[f"{cid}/i1"] = r["i1"].astype(float)
        rec[f"{cid}/i2"] = r["i2"].astype(float)
        rec[f"{cid}/i3"] = r["i3"].astype(float)
        rec[f"{cid}/tr"] = r["tr"].astype(float)
        rec[f"{cid}/bc"] = r["bc"].ravel().astype(float)
    return rec


if __name__ == "__main__":
    res = run_all()  # one untimed call, used for the records
    rec = records(res)
    py_ms = median_ms(run_all, reps=20)
    write_record("tri.find", rec, py_ms)

    r_rec = read_record("tri.find")
    py_rec = {k: np.asarray(v, dtype=float).ravel() for k, v in rec.items()}
    ok, max_diff, bad = compare(py_rec, r_rec)
    found = int(sum(np.sum(r["i1"] != 0) for r in res))
    report(
        "tri.find",
        ok,
        max_diff,
        r_rec["_r_median_ms"][0],
        py_ms,
        extra={
            "cases": len(CASES),
            "found_in_triangle": found,
            "not_found": int(sum(np.sum(r["i1"] == 0) for r in res)),
            "compared_keys": len([k for k in r_rec if not k.startswith("_")]),
            "mismatched_keys": bad if bad else "none",
        },
    )
