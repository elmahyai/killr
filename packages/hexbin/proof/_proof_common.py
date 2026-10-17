"""Shared helpers for the hexbin Python-side proofs. Run from the repository root.

Reads the R reference written by the matching `<name>_r.R` (its `<name>-r.txt`), recomputes the
same cases in Python, compares every value with an absolute tolerance of 1e-8, times the
translated call (one untimed call, then the median of 20 with time.perf_counter), and writes
`<name>-py.txt`.
"""

from __future__ import annotations

import math
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np

REPO = Path(__file__).resolve().parents[3]
PKG = REPO / "packages" / "hexbin"
OUT_DIR = PKG / "docs" / "output"
TOL = 1e-8
NA_INTEGER = -2147483648  # R's NA_integer_

# Make `import hexbin` resolve to packages/hexbin/hexbin, not to anything installed.
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))


def points_fixed(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Same formula as _proof_common.R: integer products exact in double, one division each."""
    k = np.arange(1, n + 1, dtype=np.float64)
    x = np.mod(k * 7919, 10007) / 10007 * 10 - 5
    y = np.mod(k * 104729, 10009) / 10009 * 6 - 3
    return x, y


def load_ref(name: str) -> dict[str, tuple[str, object]]:
    """Read `<name>-r.txt`. Returns key -> ("num", float array with NaN for NA) or ("str", text)."""
    path = OUT_DIR / f"{name}-r.txt"
    ref: dict[str, tuple[str, object]] = {}
    with path.open() as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split(" ", 2)
            key, kind = parts[0], parts[1]
            rest = parts[2] if len(parts) > 2 else ""
            if kind == "num":
                toks = rest.split() if rest else []
                vals = [math.nan if t == "NA" else float(t) for t in toks]
                ref[key] = ("num", np.array(vals, dtype=np.float64))
            else:
                ref[key] = ("str", rest)
    return ref


def hexvp_from_ref(ref: dict, prefix: str):
    """Build the Python HexVP from the slots that record_hexvp() wrote for `prefix`."""
    from hexbin._classes import HexVP  # noqa: E402  (PKG is already on sys.path)

    return HexVP(
        mar=ref[f"{prefix}.mar"][1],
        plt=ref[f"{prefix}.plt"][1],
        xscale=ref[f"{prefix}.xscale"][1],
        yscale=ref[f"{prefix}.yscale"][1],
        shape=float(ref[f"{prefix}.shape"][1][0]),
    )


def time_median(f: Callable[[], object], reps: int = 20) -> float:
    """One untimed call, then the median of `reps` timed calls, with perf_counter."""
    f()
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        f()
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


class Report:
    """Collects comparisons. A key matches when it has the same kind, shape and values within TOL."""

    def __init__(self, name: str):
        self.name = name
        self.lines: list[str] = []
        self.max_abs_diff = 0.0
        self.failures: list[str] = []
        self.checked = 0

    def num(self, ref: dict, key: str, got) -> None:
        self.checked += 1
        if key not in ref:
            self.failures.append(f"{key}: missing from R reference")
            return
        kind, rv = ref[key]
        if kind != "num":
            self.failures.append(f"{key}: R kind {kind}, Python numeric")
            return
        raw = np.asarray(got).ravel()
        g = raw.astype(np.float64)
        if raw.dtype.kind in "iu":
            # R's NA_integer_ is the int32 minimum; a float NaN is the same NA here.
            g[raw == NA_INTEGER] = math.nan
        if g.shape != rv.shape:
            self.failures.append(f"{key}: length R {rv.size} vs Python {g.size}")
            return
        both_nan = np.isnan(rv) & np.isnan(g)
        if np.any(np.isnan(rv) != np.isnan(g)):
            self.failures.append(f"{key}: NA positions differ")
            return
        diff = np.abs(rv[~both_nan] - g[~both_nan])
        d = float(diff.max()) if diff.size else 0.0
        self.max_abs_diff = max(self.max_abs_diff, d)
        if d > TOL:
            self.failures.append(f"{key}: max abs diff {d:.3g} > {TOL:g}")
        self.lines.append(f"  {key:<34} n={rv.size:<7} max_abs_diff={d:.3g}")

    def text(self, ref: dict, key: str, got: str) -> None:
        self.checked += 1
        if key not in ref or ref[key][0] != "str":
            self.failures.append(f"{key}: no string reference")
            return
        ok = ref[key][1] == got
        self.lines.append(f"  {key:<34} string {'equal' if ok else 'DIFFERENT'}: {got!r}")
        if not ok:
            self.failures.append(f"{key}: R {ref[key][1]!r} vs Python {got!r}")

    def write(self, r_median: float | None, py_median: float, extra: list[str] | None = None) -> bool:
        ok = not self.failures
        out = [f"{self.name}: compared {self.checked} values with R hexbin 1.28.6, tolerance {TOL:g}"]
        out += self.lines
        out.append(f"max abs diff over numeric values: {self.max_abs_diff:.3g}")
        if self.failures:
            out.append("FAILURES:")
            out += [f"  {f}" for f in self.failures]
        out.append(f"matches R: {'yes' if ok else 'no'}")
        out.append("")
        out.append("timing, one translated call (median of 20 after one untimed call, perf_counter)")
        out.append(f"  Python median seconds: {py_median:.9f}")
        if r_median is not None:
            out.append(f"  R median seconds (Sys.time): {r_median:.9f}")
            out.append(f"  speedup (R / Python): {r_median / py_median:.3f}")
        if extra:
            out += extra
        path = OUT_DIR / f"{self.name}-py.txt"
        path.write_text("\n".join(out) + "\n")
        print("\n".join(out))
        print(f"wrote {path}")
        return ok


def r_timing(ref: dict) -> float | None:
    kind_val = ref.get("timing_r_median_s")
    return None if kind_val is None else float(kind_val[1][0])
