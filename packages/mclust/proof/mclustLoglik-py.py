"""Proof: mclust.mclust_loglik.mclustLoglik against R mclust 6.1.3.

Run after proof/mclustLoglik-r.R, from packages/mclust:
    Rscript proof/mclustLoglik-r.R && python3 proof/mclustLoglik-py.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bic_proof_common import MODELS14, bic_obj, record_matrix, report, timed_median_ms  # noqa: E402
from mclust.mclust_loglik import mclustLoglik  # noqa: E402


def cases():
    A = bic_obj(range(1, 10), range(1, 11), MODELS14[:10], 150, 4, "A")
    B = bic_obj(range(2, 11), range(5, 15), MODELS14[4:14], 150, 4, "B")
    N = bic_obj(range(0, 4), range(1, 4), ["EII", "VVV", "EEE"], 200, 2, "N", noise=True)
    O = bic_obj(range(1, 5), range(1, 4), ["E", "V", "X"], 60, 1, "O")
    return [
        ("L1-A", A),
        ("L2-B", B),
        ("L3-noise-G0", N),
        ("L4-d1-X-alias", O),
    ]


CASES = cases()


def run_all():
    return [mclustLoglik(x) for _, x in CASES]


def records():
    res = run_all()
    lines = []
    for (cid, _), r in zip(CASES, res):
        lines += record_matrix(cid, r)
    return lines


if __name__ == "__main__":
    lines = records()  # one untimed call
    py_ms = timed_median_ms(run_all, reps=20)
    report("mclustLoglik", lines, py_ms)
