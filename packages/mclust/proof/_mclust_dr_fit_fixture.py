"""Banknote Mclust fit for the MclustDR summary and print proofs.

The R side builds the same input with ``MclustDR-export.R`` and
``MclustDR(mod, lambda = 0.7)``. This module reads the CSV files that script
writes and returns the translated ``MclustDR`` object.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))

from mclust.mclust_dr import mclust_dr  # noqa: E402


def _is_numeric(row: list[str]) -> bool:
    try:
        [float(x) for x in row]
    except ValueError:
        return False
    return True


def read_table(path: Path) -> np.ndarray:
    """Read a ``write.csv`` file, skipping its quoted header row."""
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    if rows and not _is_numeric(rows[0]):
        rows = rows[1:]
    return np.asarray([[float(x) for x in row] for row in rows], dtype=float)


def load_mod() -> dict:
    meta = (PROOF / "MclustDR_meta.txt").read_text().splitlines()
    g = int(meta[0])
    sigma = np.stack([read_table(PROOF / f"MclustDR_sigma_{i}.csv") for i in range(1, g + 1)], axis=2)
    return {
        "data": read_table(PROOF / "MclustDR_data.csv"),
        "G": g,
        "modelName": meta[1],
        "hypvol": float("nan") if meta[2] == "NA" else float(meta[2]),
        "classification": read_table(PROOF / "MclustDR_classification.csv")[:, 0].astype(int),
        "parameters": {
            "pro": read_table(PROOF / "MclustDR_pro.csv")[:, 0],
            "mean": read_table(PROOF / "MclustDR_mean.csv"),
            "variance": {"sigma": sigma},
        },
    }


def load_dr() -> dict:
    """Return ``MclustDR(mod, lambda = 0.7)`` from the translated code."""
    return mclust_dr(load_mod(), lambda_=0.7)
