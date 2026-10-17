"""Shared helpers for the per-class coverage proofs (Initialize, logDet, recalc).

Each class proof prints one JSON object with one entry per function:
``{"Initialize": {"value": [...], "median_ms": ...}, "logDet": {...}, "recalc": {...}}``.
A function that raises in Python prints ``{"error": "..."}`` in place of ``value``.
Each function gets one untimed call, then the median of 20 timed calls.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
import types
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load_nlme() -> None:
    """Make ``nlme`` importable without running ``nlme/__init__.py`` (it imports phenoModel)."""
    sys.path.insert(0, str(ROOT))
    if "nlme" not in sys.modules:
        pkg = types.ModuleType("nlme")
        pkg.__path__ = [str(ROOT / "nlme")]
        sys.modules["nlme"] = pkg


def timed(fn: Callable[[], object]) -> dict:
    """One untimed call, then the median of 20 timed calls (milliseconds)."""
    try:
        value = np.ravel(np.asarray(fn(), dtype=np.float64))
    except Exception as exc:  # the error is reported, not hidden
        return {"error": f"{type(exc).__name__}: {exc}"}
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        fn()
        elapsed.append((time.perf_counter() - started) * 1000)
    return {"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}


def emit(results: dict) -> None:
    print(json.dumps(results))
