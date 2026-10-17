"""Proof: mclust.model_metadata.dupPartition and hc with that partition, against R mclust 6.1.3.

Run from packages/mclust, after proof/dupPartition-r.R:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/dupPartition-py.py
Writes docs/output/dupPartition-py.txt with the same record layout as dupPartition-r.txt.
"""

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mclust.hc import hc  # noqa: E402
from mclust.model_metadata import dupPartition  # noqa: E402

ia = np.arange(1, 41)
xc = ((ia * 37) % 11) / 11 + 0.1 * ia / 40
xfa = np.loadtxt(ROOT / "proof" / "mclust_faithful.csv", delimiter=",")


def fmt(v):
    v = float(v)
    if math.isnan(v):
        return "NA"
    return "%.17g" % v


def rec(key, x):
    arr = np.asarray(x, dtype=float).ravel(order="F")
    return "\t".join([key] + [fmt(v) for v in arr])


def one():
    return {
        "DPfa": dupPartition(xfa),
        "DPsmall": dupPartition(np.array([1.0, 1.0, 2.0, 2.0])),
        "DPc": dupPartition(xc),
        "HCdefault": hc(xfa, modelName="VVV", use="SVD"),
        "HCpart": hc(xfa, modelName="VVV", use="SVD", partition=dupPartition(xfa)),
    }


if __name__ == "__main__":
    fits = one()
    lines = [
        rec("DPfa", fits["DPfa"]),
        rec("DPsmall", fits["DPsmall"]),
        rec("DPc", fits["DPc"]),
        rec("HCdefault", fits["HCdefault"]),
        rec("HCdefault.initialPartition", fits["HCdefault"].initialPartition),
        rec("HCpart", fits["HCpart"]),
        rec("HCpart.initialPartition", fits["HCpart"].initialPartition),
    ]
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000.0)
    lines.append(f"time_ms\t{'%.17g' % statistics.median(elapsed)}")
    out = ROOT / "docs" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dupPartition-py.txt").write_text("\n".join(lines) + "\n")
    print("Python dupPartition median ms:", statistics.median(elapsed))
