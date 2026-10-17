"""Proof: mclust.mclust_bic_update.mclustBICupdate against R mclust 6.1.3.

Run after proof/mclustBICupdate-r.R, from packages/mclust:
    Rscript proof/mclustBICupdate-r.R && python3 proof/mclustBICupdate-py.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bic_proof_common import MODELS14, bic_obj, record_matrix, report, timed_median_ms  # noqa: E402
from mclust.mclust_bic_update import mclustBICupdate  # noqa: E402


def objs():
    A = bic_obj(range(1, 10), range(1, 11), MODELS14[:10], 150, 4, "A")
    A2 = bic_obj(range(1, 10), range(1, 11), MODELS14[:10], 150, 4, "A2")
    B = bic_obj(range(2, 11), range(5, 15), MODELS14[4:14], 150, 4, "B")
    C = bic_obj(range(1, 10), range(11, 15), MODELS14[10:14], 150, 4, "C", cls="mclustICL")
    return A, A2, B, C


def cases():
    A, A2, B, C = objs()
    return [
        ("U1-A-B", lambda: mclustBICupdate(A, B)),
        ("U2-A-B-C", lambda: mclustBICupdate(A, B, C)),
        ("U3-A-NULL", lambda: mclustBICupdate(A, None)),
        ("U4-NULL-B", lambda: mclustBICupdate(None, B)),
        ("U5-A-A2-tie", lambda: mclustBICupdate(A, A2)),
        ("U6-A2-A-tie", lambda: mclustBICupdate(A2, A)),
        ("U7-B-A", lambda: mclustBICupdate(B, A)),
        ("U8-C-A-B", lambda: mclustBICupdate(C, A, B)),
    ]


CASES = cases()


def run_all():
    return [fn() for _, fn in CASES]


def records():
    res = run_all()
    lines = []
    for (cid, _), r in zip(CASES, res):
        lines += record_matrix(cid, r)
    return lines


if __name__ == "__main__":
    lines = records()  # one untimed call
    py_ms = timed_median_ms(run_all, reps=20)
    report("mclustBICupdate", lines, py_ms)
