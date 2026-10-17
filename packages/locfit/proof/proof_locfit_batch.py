"""Fixed-input R/Python proof runner for the requested locfit exports."""
from __future__ import annotations

import importlib
import statistics
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
X = np.linspace(0.05, 0.95, 20)[:, None]
Y = np.sin(2 * np.pi * X[:, 0])
NAMES = ["lfmarg", "locfit", "locfit.censor", "locfit.matrix",
         "locfit.quasi", "locfit.raw", "locfit.robust", "lp",
         "lscv", "lscv.exact"]


def flatten(value):
    if isinstance(value, dict):
        return np.concatenate([flatten(v) for v in value.values() if np.asarray(v).dtype.kind in "fiu"])
    if isinstance(value, (list, tuple, np.ndarray)):
        return np.asarray(value, dtype=float).reshape(-1)
    return np.asarray([value], dtype=float)


def main():
    for name in NAMES:
        module, fn = name.replace(".", "_"), name.replace(".", "_")
        try:
            fun = getattr(importlib.import_module(f"packages.locfit.{module}"), fn)
            value = fun(X, Y)
        except Exception as exc:
            (ROOT / f"{name}_python.txt").write_text(f"ERROR {exc}\n")
            continue
        elapsed = []
        for _ in range(20):
            started = time.perf_counter()
            fun(X, Y)
            elapsed.append(time.perf_counter() - started)
        np.savetxt(ROOT / f"{name}_python.txt", flatten(value), fmt="%.17g")
        rfile = ROOT / f"{name}_r.txt"
        if rfile.exists() and not rfile.read_text().startswith("ERROR"):
            r = np.loadtxt(rfile, ndmin=1)
            p = flatten(value)
            diff = float(np.max(np.abs(r - p))) if r.shape == p.shape else float("inf")
            print(f"{name},matches={'yes' if diff <= 1e-8 else 'no'},max_abs_diff={diff:.17g},"
                  f"translated_ms={statistics.median(elapsed)*1000:.9g}")
        else:
            print(f"{name},matches=no,max_abs_diff=blocked,r_ms=blocked,"
                  f"translated_ms={statistics.median(elapsed)*1000:.9g},speedup=blocked")


if __name__ == "__main__":
    main()
