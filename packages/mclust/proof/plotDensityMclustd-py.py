"""Python side of the plotDensityMclustd proof (pairwise density panels, d = 3 and d = 4).

Reads the fits that plotDensityMclustd-r.R dumped, draws each case with the recording
log, and writes plotDensityMclustd-py.txt in the format plot_record.R writes. The timed
case is the d = 3 fit with no points: one untimed call, then the median of 20 calls.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
sys.path.insert(0, str(PROOF))

from plot_proof_common import OUT, _NoRecord, run_proof  # noqa: E402  sets the Agg backend
import matplotlib.pyplot as plt  # noqa: E402

from plot_object_io import read_mclust_object  # noqa: E402
from mclust.plot_density_mclust import plotDensityMclustd  # noqa: E402
from mclust.plot_log import PlotLog  # noqa: E402

d3 = read_mclust_object(PROOF / "plot_object_density3d.json")
d4 = read_mclust_object(PROOF / "plot_object_density4d.json")
pts = d3["data"][:30]


def _case(obj, **kwargs):
    def run(fig, ax, log):
        plotDensityMclustd(obj, ax=ax, log=log, **kwargs)
    return run


cases = {
    "d3_contour": _case(d3),
    "d3_points": _case(d3, data=pts, points_col="black"),
    "d4_contour": _case(d4),
}

stem = "plotDensityMclustd"
ms = run_proof(stem, cases, timed="d3_contour")

# The d = 4 fit is timed the same way, for the record.
def _once_d4() -> None:
    log = PlotLog()
    log.log = _NoRecord()
    plotDensityMclustd(d4, ax=None, log=log)


_once_d4()
times = []
for _ in range(20):
    t0 = time.perf_counter()
    _once_d4()
    times.append((time.perf_counter() - t0) * 1000.0)
ms4 = statistics.median(times)
(OUT / f"{stem}-d4-py-time.txt").write_text(f"{ms4:.17g}\n")

# Figures of the Python drawing, for the docs: d = 3 with points, and d = 4.
for name, obj, kwargs in [("", d3, {"data": pts, "points_col": "black"}), ("-d4", d4, {})]:
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)
    plotDensityMclustd(obj, ax=ax, log=PlotLog(), **kwargs)
    fig.savefig(OUT / f"{stem}{name}-python.svg")
    plt.close(fig)

print(f"translated_ms {ms:.17g}")
print(f"translated_ms_d4 {ms4:.17g}")
