"""Proof: interp.tri_sht2tri.tri_sht2tri against R interp 1.1-6 triSht2tri.

Run after proof/triSht2tri-r.R, from packages/interp:
    Rscript proof/triSht2tri-r.R && python3 proof/triSht2tri-py.py
The comparison is exact on the integer lists, which is stricter than
comparing canonicalised triangles.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

from interp_proof_common import compare, median_ms, point_cases, read_record, report, write_record  # noqa: E402
from interp.tri_mesh import tri_mesh  # noqa: E402
from interp.tri_sht2tri import tri_sht2tri  # noqa: E402

CASES = [c for c in point_cases() if c["id"] != "dups-strip"]
TRIS = [tri_mesh(c["x"], c["y"], duplicate=c["dup"]) for c in CASES]


def run_all():
    return [tri_sht2tri(t) for t in TRIS]


def records(results):
    rec = {}
    for c, o in zip(CASES, results):
        cid = c["id"]
        rec[f"{cid}/n"] = o["n"]
        rec[f"{cid}/x"] = o["x"]
        rec[f"{cid}/y"] = o["y"]
        rec[f"{cid}/tlist"] = o["tlist"]
        rec[f"{cid}/tlptr"] = o["tlptr"]
        rec[f"{cid}/tlend"] = o["tlend"]
        rec[f"{cid}/tlnew"] = o["tlnew"]
        rec[f"{cid}/adjlen"] = [len(a) for a in o["adjlist"]]
        rec[f"{cid}/adj"] = np.concatenate(o["adjlist"])
    return rec


if __name__ == "__main__":
    results = run_all()  # one untimed call, used for the records
    rec = records(results)
    py_ms = median_ms(run_all, reps=20)
    write_record("triSht2tri", rec, py_ms)

    r_rec = read_record("triSht2tri")
    py_rec = {k: np.asarray(v, dtype=float).ravel() for k, v in rec.items()}
    ok, max_diff, bad = compare(py_rec, r_rec)
    report(
        "triSht2tri",
        ok,
        max_diff,
        r_rec["_r_median_ms"][0],
        py_ms,
        extra={
            "cases": len(CASES),
            "compared_keys": len([k for k in r_rec if not k.startswith("_")]),
            "mismatched_keys": bad if bad else "none",
        },
    )
