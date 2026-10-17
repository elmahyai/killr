"""Proof: mclust.pick_bic.pickBIC against R mclust 6.1.3 on the same fixtures.

Run after proof/pickBIC-r.R, from packages/mclust:
    Rscript proof/pickBIC-r.R && python3 proof/pickBIC-py.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import warnings  # noqa: E402

from bic_proof_common import (  # noqa: E402
    bic_obj, record_pick, report, timed_median_ms, MODELS14,
)
from mclust.pick_bic import pickBIC  # noqa: E402


def A():
    return bic_obj(range(1, 10), range(1, 11), MODELS14[:10], 150, 4, "A")


def B():
    return bic_obj(range(2, 11), range(5, 15), MODELS14[4:14], 150, 4, "B")


def E():
    return bic_obj(range(1, 3), range(1, 3), MODELS14[:2], 150, 4, "E")


def D():
    obj = bic_obj(range(1, 4), range(1, 3), MODELS14[:2], 150, 4, "D")
    obj["values"][:] = float("nan")
    return obj


CASES = [
    ("A-k3", A, 3),
    ("A-k1", A, 1),
    ("B-k5", B, 5),
    ("E-k10", E, 10),
    ("D-allNA-k3", D, 3),
    ("scalar-k3", None, 3),
]


def run_all():
    out = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for _, make, k in CASES:
            x = make() if make is not None else 5.0
            out.append(pickBIC(x, k=k))
    return out


def records():
    res = run_all()
    lines = []
    for (cid, _, _), r in zip(CASES, res):
        lines += record_pick(cid, r)
    return lines


if __name__ == "__main__":
    lines = records()  # one untimed call
    py_ms = timed_median_ms(run_all, reps=20)
    report("pickBIC", lines, py_ms)
