"""Proof: interp.tri_mesh.tri_mesh against R interp 1.1-6 tri.mesh.

Run after proof/tri.mesh-r.R, from packages/interp:
    Rscript proof/tri.mesh-r.R && python3 proof/tri.mesh-py.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

from interp_proof_common import (  # noqa: E402
    canon_tri,
    compare,
    median_ms,
    point_cases,
    read_record,
    report,
    write_record,
)
from interp.tri_mesh import tri_mesh  # noqa: E402

CASES = point_cases()


def run_all():
    return [tri_mesh(c["x"], c["y"], duplicate=c["dup"]) for c in CASES]


def records(results):
    rec = {}
    for c, t in zip(CASES, results):
        cid = c["id"]
        ct, cc = canon_tri(t["trlist"], t["cclist"])
        rec[f"{cid}/n"] = t["n"]
        rec[f"{cid}/x"] = t["x"]
        rec[f"{cid}/y"] = t["y"]
        rec[f"{cid}/nt"] = t["nt"]
        rec[f"{cid}/nchull"] = t["nchull"]
        rec[f"{cid}/chull"] = t["chull"]
        rec[f"{cid}/narcs"] = t["narcs"]
        rec[f"{cid}/arcs"] = t["arcs"]
        rec[f"{cid}/tri"] = ct
        rec[f"{cid}/cc"] = cc
        rec[f"{cid}/trlist_raw"] = t["trlist"]
    return rec


if __name__ == "__main__":
    results = run_all()  # one untimed call, used for the records
    rec = records(results)
    py_ms = median_ms(run_all, reps=20)
    write_record("tri.mesh", rec, py_ms)

    r_rec = read_record("tri.mesh")
    py_rec = {k: np.asarray(v, dtype=float).ravel() for k, v in rec.items()}
    ok, max_diff, bad = compare(py_rec, r_rec)
    raw_ok = all(
        np.array_equal(py_rec[k], r_rec[k])
        for k in r_rec
        if k.endswith("/trlist_raw") or k.endswith("/chull") or k.endswith("/arcs")
    )
    report(
        "tri.mesh",
        ok,
        max_diff,
        r_rec["_r_median_ms"][0],
        py_ms,
        extra={
            "cases": len(CASES),
            "compared_keys": len([k for k in r_rec if not k.startswith("_")]),
            "raw_order_identical_trlist_chull_arcs": raw_ok,
            "mismatched_keys": bad if bad else "none",
        },
    )
