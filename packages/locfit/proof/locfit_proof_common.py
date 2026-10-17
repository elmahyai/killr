"""Shared helpers for the locfit Python proofs (run from the repository root).

Each proof reads the fixed inputs and the R reference values written by the
matching ``<name>_r.R`` script, calls the translated function, compares the
two within 1e-8, and times both sides.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import math
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "packages/locfit/docs/output"
MODULE_DIR = ROOT / "packages/locfit/locfit"
TOL = 1e-8


def load(name: str):
    """Import ``locfit/<name>.py`` under the alias package ``lfpy``.

    The installed Rust wheel named ``locfit`` shadows a plain import of this
    directory, so the modules are imported under ``lfpy`` instead. Relative
    imports such as ``from ._common import field`` still resolve.
    """
    if "lfpy" not in sys.modules:
        pkg = types.ModuleType("lfpy")
        pkg.__path__ = [str(MODULE_DIR)]
        sys.modules["lfpy"] = pkg
    return importlib.import_module(f"lfpy.{name}")


def read_fixture(name: str):
    return json.loads((OUT / f"locfit_{name}_fixture.json").read_text())


def read_r_output(name: str):
    return json.loads((OUT / f"locfit_{name}_r.json").read_text())


def read_r_timing(name: str) -> float:
    text = (OUT / f"locfit_{name}_r_timing.txt").read_text().strip()
    return float(text.split("=", 1)[1])


def to_plain(value):
    """Convert translated outputs (dataclasses, arrays, numpy scalars) to JSON-like values."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return to_plain(value.tolist())
    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def time_py_ms(fn) -> float:
    """Median per-call time in ms: one untimed call, then 20 samples of a 20-call loop."""
    fn()
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(20):
            fn()
        samples.append((time.perf_counter() - start) * 1000.0 / 20)
    return statistics.median(samples)


def _num(x):
    return math.nan if x is None else float(x)


def compare(r, p, path: str, state: dict) -> None:
    """Recursive comparison of R JSON (``r``) against plain Python values (``p``).

    R length-1 vectors are written as one-element arrays, so a one-element array
    on either side is matched against a scalar on the other side. NA (JSON null)
    matches NaN. Strings must be equal. Numbers must agree within ``TOL``.
    """
    if isinstance(r, list) and len(r) == 1 and not isinstance(p, list):
        r = r[0]
    if isinstance(p, list) and len(p) == 1 and not isinstance(r, list):
        p = p[0]
    if isinstance(r, dict) or isinstance(p, dict):
        if not (isinstance(r, dict) and isinstance(p, dict)) or set(r) != set(p):
            state["bad"].append(f"{path}: names differ")
            return
        for key in r:
            compare(r[key], p[key], f"{path}.{key}", state)
        return
    if isinstance(r, list) or isinstance(p, list):
        if not (isinstance(r, list) and isinstance(p, list)) or len(r) != len(p):
            state["bad"].append(f"{path}: shape differs")
            return
        for i, (a, b) in enumerate(zip(r, p)):
            compare(a, b, f"{path}[{i}]", state)
        return
    if isinstance(r, str) or isinstance(p, str):
        if r != p:
            state["bad"].append(f"{path}: {r!r} != {p!r}")
        return
    a, b = _num(r), _num(p)
    if math.isnan(a) or math.isnan(b):
        if not (math.isnan(a) and math.isnan(b)):
            state["bad"].append(f"{path}: NA/NaN mismatch")
        return
    diff = abs(a - b)
    state["max"] = max(state["max"], diff)
    if diff > TOL:
        state["bad"].append(f"{path}: {a!r} vs {b!r} (diff {diff:.3g})")


def new_state() -> dict:
    return {"max": 0.0, "bad": []}


def report(name: str, case_lines: list[str], state: dict, r_ms: float, py_ms: float) -> str:
    """Write ``locfit_<name>_compare.txt`` and return the summary row."""
    matches = "yes" if not state["bad"] else "no"
    speedup = r_ms / py_ms if py_ms > 0 else math.nan
    row = (f"{name},matches={matches},max_abs_diff={state['max']:.3g},"
           f"r_ms={r_ms:.6g},translated_ms={py_ms:.6g},speedup={speedup:.4g}")
    lines = [row] + case_lines + [f"mismatch: {m}" for m in state["bad"]]
    (OUT / f"locfit_{name}_compare.txt").write_text("\n".join(lines) + "\n")
    return row


def check_case(name: str, r_value, p_value, total: dict, lines: list[str]) -> None:
    """Compare one case and fold its result into the running total."""
    st = new_state()
    compare(r_value, p_value, name, st)
    total["max"] = max(total["max"], st["max"])
    total["bad"].extend(st["bad"])
    lines.append(f"case={name} matches={'yes' if not st['bad'] else 'no'} "
                 f"max_abs_diff={st['max']:.3g}")


def write_python_output(name: str, value) -> None:
    (OUT / f"locfit_{name}_python.json").write_text(json.dumps(value, indent=1) + "\n")
