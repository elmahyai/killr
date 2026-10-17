"""Deutanomaly CVD conversion tables (colorspace 2.1-4)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np


@lru_cache(maxsize=1)
def deutanomaly_cvd() -> dict[str, np.ndarray]:
    """Machado RGB transform matrices for deutanomaly at severities ``0`` through ``10``."""
    path = Path(__file__).resolve().parent / "deutanomaly_cvd.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(index): np.asarray(flat, dtype=np.float64).reshape(3, 3)
        for index, flat in enumerate(raw)
    }
