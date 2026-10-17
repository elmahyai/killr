"""Shared MclustDR fixture for subsel proofs (R-exported directions)."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent


def _read_matrix(path: Path) -> np.ndarray:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        try:
            [float(x) for x in header]
            rows = [[float(x) for x in header]]
        except ValueError:
            rows = []
        rows.extend([[float(x) for x in row] for row in reader])
    return np.asarray(rows, dtype=float)


def load_dr_fixture() -> dict:
    x = _read_matrix(PROOF / "MclustDR_data.csv")
    direction = _read_matrix(PROOF / "MclustDRsubsel_dir.csv")
    return {
        "type": (PROOF / "MclustDRsubsel_type.txt").read_text().strip(),
        "x": x,
        "dir": direction,
        "numdir": int((PROOF / "MclustDRsubsel_numdir.txt").read_text()),
        "lambda": float((PROOF / "MclustDRsubsel_lambda.txt").read_text()),
        "classification": _read_matrix(PROOF / "MclustDR_classification.csv").astype(int).reshape(-1),
    }
