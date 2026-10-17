"""Shared runner for the mclust plot proofs.

``run_proof(stem, cases, timed)`` runs every case with a Matplotlib axes and the
recording log, writes ``<stem>-py.txt`` in the format ``proof/plot_record.R``
writes, then times the case named ``timed``: one untimed call and the median of
20 timed calls. The timed calls pass no axes and keep no record, which is the
Python side of R's time mode (no drawing, no record).
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PROOF) not in sys.path:
    sys.path.insert(0, str(PROOF))

from mclust.plot_log import PlotLog, log_lines  # noqa: E402

OUT = ROOT / "docs" / "output"

Case = Callable[..., None]


class _NoRecord(list):
    """A log that drops every entry, used for the timed calls."""

    def append(self, item):  # noqa: D102
        return None


def run_proof(stem: str, cases: dict[str, Case], timed: str) -> float:
    OUT.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    for name, case in cases.items():
        fig = plt.figure()
        ax = fig.add_subplot(111)
        log = PlotLog()
        case(fig, ax, log)
        out.append(f"CASE {name}")
        out.extend(log_lines(log))
        plt.close(fig)
    (OUT / f"{stem}-py.txt").write_text("\n".join(out) + "\n")

    fn = cases[timed]

    def once() -> None:
        log = PlotLog()
        log.log = _NoRecord()
        fn(None, None, log)

    once()
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        once()
        times.append(time.perf_counter() - t0)
    ms = statistics.median(times) * 1000.0
    (OUT / f"{stem}-py-time.txt").write_text(f"{ms:.17g}\n")
    return ms
