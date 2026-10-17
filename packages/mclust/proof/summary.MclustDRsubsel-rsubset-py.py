"""Check summary.MclustDRsubsel against R, fed R's own MclustDRsubsel output.

The subset object comes from summary.MclustDRsubsel-rsubset-export.R, so this
checks the summary step alone. The end-to-end chain (Python subset fit) is in
summary.MclustDRsubsel-py.py.
"""

import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
PKG = PROOF.parent
sys.path.insert(0, str(PKG))

from mclust.print_mclust_dr import _summary_text, summary_MclustDRsubsel  # noqa: E402


def _read_csv_matrix(path: Path) -> np.ndarray:
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))[1:]
    return np.asarray([[float(x) for x in row] for row in rows], dtype=float)


def _read_labels(path: Path) -> list[str]:
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))[1:]
    return [row[0] for row in rows]


def load_r_subset() -> dict:
    meta = (PROOF / "summary.MclustDRsubsel_R_meta.txt").read_text().splitlines()
    return {
        "type": meta[0],
        "modelName": meta[1],
        "G": int(meta[2]),
        "numdir": int(meta[3]),
        "lambda": float(meta[4]),
        "classification": _read_labels(PROOF / "summary.MclustDRsubsel_R_classification.csv"),
        "basisx": _read_csv_matrix(PROOF / "summary.MclustDRsubsel_R_basisx.csv"),
        "std.basisx": _read_csv_matrix(PROOF / "summary.MclustDRsubsel_R_std_basisx.csv"),
        "evalues": np.loadtxt(PROOF / "summary.MclustDRsubsel_R_evalues.txt"),
    }


def flat(s: dict) -> np.ndarray:
    return np.concatenate([
        np.asarray(s["n"], dtype=float),
        np.asarray([s["G"]], dtype=float),
        np.asarray(s["basis"], dtype=float).reshape(-1, order="F"),
        np.asarray(s["std.basis"], dtype=float).reshape(-1, order="F"),
        np.asarray(s["evalues"], dtype=float),
        np.asarray(s["evalues.cumperc"], dtype=float),
    ])


def one(sub: dict) -> dict:
    return summary_MclustDRsubsel(sub)


sub = load_r_subset()

# untimed call: numeric values and printed text
s = one(sub)
ref = np.loadtxt(PROOF / "summary.MclustDRsubsel-r-values.txt")
value = flat(s)
if value.shape != ref.shape:
    max_abs = float("inf")
else:
    max_abs = float(np.max(np.abs(value - ref)))
matches = max_abs <= 1e-8
(PROOF.parent / "docs" / "output" / "summary.MclustDRsubsel-rsubset-py.txt").write_text(_summary_text(s))

# timed: median of 20 calls of the summary alone
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(sub)
    elapsed.append((time.perf_counter() - started) * 1000)

print(f"matches {'true' if matches else 'false'}")
print(f"max_abs_diff {max_abs:.17g}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
