"""Proof for surfacePlot, including perspective and swapped-axis data."""

import statistics
import time
from pathlib import Path

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof, _NoRecord
from mclust.surface_plot import surfacePlot
from mclust.plot_log import PlotLog

fx = make_fixtures()
PS = {"pro": fx["pro"], "mean": fx["mu2"], "variance": {"sigma": fx["sig2"]}}
PS2 = {"pro": [0.4, 0.6], "mean": fx["mu2"][:, :2],
       "variance": {"sigma": fx["sig2"][:, :, :2]}}


def pal(n):
    return [("#1E90FF", "#FFA500")[k % 2] for k in range(n)]


def record(call, fig, ax, log):
    result = call(ax=ax, log=log)
    for name in ("x", "y", "z"):
        value = result[name]
        if hasattr(value, "ravel"):
            value = value.ravel(order="F")
        log.log.append(("V", [name, value]))
    return result


calls = {
    "contour_density": lambda **kw: surfacePlot(fx["data2"], PS, **kw),
    "contour_uncertainty": lambda **kw: surfacePlot(
        fx["data2"], PS, what="uncertainty", **kw),
    "hdr_density": lambda **kw: surfacePlot(fx["data2"], PS, type="hdr", **kw),
    "image_density": lambda **kw: surfacePlot(
        fx["data2"], PS, type="image", col_palette=pal, **kw),
    "persp_density": lambda **kw: surfacePlot(
        fx["data2"], PS, type="persp", grid=25, nlevels=1, **kw),
    "swap_axes": lambda **kw: surfacePlot(
        fx["data2"], PS2, swapAxes=True, grid=25, **kw),
}

cases = {name: (lambda fig, ax, log, call=call: record(call, fig, ax, log))
         for name, call in calls.items()}

if __name__ == "__main__":
    ms = run_proof("surfacePlot", cases, timed="contour_density")
    out = Path(__file__).resolve().parent.parent / "docs" / "output"
    for name, call in calls.items():
        def once():
            log = PlotLog()
            log.log = _NoRecord()
            call(ax=None, log=log)
        once()
        times = []
        for _ in range(20):
            t0 = time.perf_counter()
            once()
            times.append(time.perf_counter() - t0)
        (out / f"surfacePlot-{name}-py-time.txt").write_text(
            f"{statistics.median(times) * 1000.0:.17g}\n")
    print(f"surfacePlot python median ms {ms:.6g}")
