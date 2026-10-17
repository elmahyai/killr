"""Proof: mclust.bic.bic against R mclust 6.1.3 on the same scalar inputs.

Run after proof/bic-r.R, from packages/mclust:
    Rscript proof/bic-r.R && python3 proof/bic-py.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bic_proof_common import record_value, report, timed_median_ms  # noqa: E402
from mclust.bic import bic  # noqa: E402

CASES = [
    ("VVV-G3-d4", "VVV", -1234.5, 150, 4, 3, False, False),
    ("X-G2-d1-noise", "X", -500.25, 100, 1, 2, True, False),
    ("EEE-G0-noise", "EEE", -800.125, 150, 4, 0, True, False),
    ("EII-G5-eqPro", "EII", -700.0, 150, 4, 5, False, True),
    ("XII-G4-d3", "XII", -650.5, 120, 3, 4, False, False),
    ("XXX-G4-noiseEq", "XXX", -640.75, 120, 3, 4, True, True),
    ("VEV-G2-d6", "VEV", -900.25, 200, 6, 2, False, False),
    ("EVV-G1-noise", "EVV", -901.0, 80, 2, 1, True, False),
    ("E-G3-d1", "E", -100.5, 50, 1, 3, False, False),
]


def run_all():
    return [
        bic(m, ll, n, d, G, noise=noise, equalPro=eq)
        for _, m, ll, n, d, G, noise, eq in CASES
    ]


def records():
    res = run_all()
    lines = []
    for (cid, *_), v in zip(CASES, res):
        lines += record_value(cid, v)
    return lines


if __name__ == "__main__":
    lines = records()  # one untimed call
    py_ms = timed_median_ms(run_all, reps=20)
    report("bic", lines, py_ms)
