"""Shared runner for the quantreg plot proofs.

``read_r_cases`` reads the log that ``plot_record.R`` wrote. ``compare`` checks
the Python log token by token: text tokens must be equal, and numeric tokens
must agree within 1e-8. ``time_median_ms`` does one untimed call and then the
median of 20 timed calls. A figure is made before each timed call and closed
after it, so the time is the plot function itself; R opens its device before
the timed calls in the same way.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
OUT = ROOT / "docs" / "output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOL = 1e-8


def read_r_cases(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("CASE "):
            current = line[5:]
            out[current] = []
        elif current is not None and line.strip():
            out[current].append(line)
    return out


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def compare(r_lines: list[str], py_lines: list[str]) -> tuple[bool, float, int, str]:
    """Returns (matches, max_abs_diff, numbers compared, first mismatch)."""
    if len(r_lines) != len(py_lines):
        return False, float("inf"), 0, f"line count R {len(r_lines)} Python {len(py_lines)}"
    worst = 0.0
    count = 0
    for k, (rl, pl) in enumerate(zip(r_lines, py_lines)):
        rt = rl.split(" ")
        pt = pl.split(" ")
        if len(rt) != len(pt):
            return False, float("inf"), count, f"line {k}: token count differs"
        for a, b in zip(rt, pt):
            if _is_number(a) and _is_number(b):
                count += 1
                diff = abs(float(a) - float(b))
                if diff > TOL:
                    return False, diff, count, f"line {k}: {a} vs {b}"
                worst = max(worst, diff)
            elif a != b:
                return False, float("inf"), count, f"line {k}: {a!r} vs {b!r}"
    return True, worst, count, ""


def time_median_ms(make_fig, fn) -> float:
    """fn(fig) timed; make_fig() runs outside the timer."""
    fig = make_fig()
    fn(fig)
    plt.close(fig)
    times = []
    for _ in range(20):
        fig = make_fig()
        started = time.perf_counter()
        fn(fig)
        times.append((time.perf_counter() - started) * 1000)
        plt.close(fig)
    return statistics.median(times)


def time_median_call_ms(fn) -> float:
    """fn() timed with no figure, for functions that draw nothing."""
    fn()
    times = []
    for _ in range(20):
        started = time.perf_counter()
        fn()
        times.append((time.perf_counter() - started) * 1000)
    return statistics.median(times)


def new_figure():
    return plt.figure(figsize=(7, 7))
