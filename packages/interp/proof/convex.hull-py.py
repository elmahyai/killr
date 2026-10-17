"""Proof: interp.convex_hull.convex_hull against R interp 1.1-6 convex.hull (plot.it = FALSE).

Run after proof/convex.hull-r.R, from packages/interp:
    Rscript proof/convex.hull-r.R && python3 proof/convex.hull-py.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

from interp_proof_common import compare, median_ms, point_cases, read_record, report, write_record  # noqa: E402
from interp.tri_mesh import tri_mesh  # noqa: E402
from interp.convex_hull import convex_hull  # noqa: E402

KEEP = {"rand60", "rand200", "grid5", "scaled40", "quad4", "dups-remove"}
CASES = [c for c in point_cases() if c["id"] in KEEP]
TRIS = [tri_mesh(c["x"], c["y"], duplicate=c["dup"]) for c in CASES]


def run_all():
    return [convex_hull(t) for t in TRIS]


def records(res):
    rec = {}
    for c, r in zip(CASES, res):
        cid = c["id"]
        rec[f"{cid}/x"] = r["x"]
        rec[f"{cid}/y"] = r["y"]
        rec[f"{cid}/i"] = r["i"].astype(float)
    return rec


if __name__ == "__main__":
    res = run_all()  # one untimed call, used for the records
    rec = records(res)
    py_ms = median_ms(run_all, reps=20)
    write_record("convex.hull", rec, py_ms)

    r_rec = read_record("convex.hull")
    py_rec = {k: np.asarray(v, dtype=float).ravel() for k, v in rec.items()}
    ok, max_diff, bad = compare(py_rec, r_rec)
    report(
        "convex.hull",
        ok,
        max_diff,
        r_rec["_r_median_ms"][0],
        py_ms,
        extra={
            "cases": len(CASES),
            "hull_vertices": int(sum(len(r["i"]) for r in res)),
            "compared_keys": len([k for k in r_rec if not k.startswith("_")]),
            "mismatched_keys": bad if bad else "none",
        },
    )
