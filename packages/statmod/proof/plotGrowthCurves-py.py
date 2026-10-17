import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from statmod.plot_growth_curves import plotGrowthCurves

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)


def curves():
    return np.array(
        [
            [1.0, 1.4, 1.2, 1.1],
            [2.0, 2.2, np.nan, 2.4],
            [1.2, 1.0, 1.5, 1.3],
            [2.4, 2.1, 2.6, 2.0],
            [3.0, 3.3, 2.8, 3.1],
            [2.2, 1.9, 2.3, 2.5],
            [0.2, 0.4, 0.3, 0.5],
        ],
        dtype=float,
    )


def curve_group():
    return np.array(["B", "A", "B", "A", "C", "A", None], dtype=object)


def _flat(drawn):
    parts = [
        np.asarray(drawn["usr"], dtype=float).reshape(-1),
        np.array([drawn["legend_x"], drawn["legend_y"]], dtype=float),
        np.asarray(drawn["y"], dtype=float).reshape(-1, order="F"),
        np.asarray(drawn["line_rgb"], dtype=float).reshape(-1, order="F"),
        np.asarray(drawn["legend_rgb"], dtype=float).reshape(-1, order="F"),
    ]
    return np.concatenate(parts)


def _call(*args, **kwargs):
    drawn = plotGrowthCurves(*args, **kwargs)
    values = _flat(drawn)
    plt.close(drawn["figure"])
    return values


def one():
    return np.concatenate(
        [
            _call(curve_group(), curves(), times=[1, 2, 4], col=[2, 4, "darkgreen"]),
            _call(
                np.array(["A", "A", "B", "B"]),
                np.array([[5.0], [5.5], [8.0], [9.0]], dtype=float),
            ),
            _call(
                np.array(["A", "A", "B", "B"]),
                np.array([[1.0, 10.0], [2.0, 20.0], [30.0, 50.0], [25.0, 80.0]], dtype=float),
                log="y",
            ),
            _call(
                np.array(["A", "A", "B", "B"]),
                np.array([[1.0, 2.0], [1.2, 2.2], [3.0, 4.0], [3.2, 3.8]], dtype=float),
                col=2,
            ),
            _call(
                np.array([10, 2, 10, 2], dtype=float),
                np.array([[1.0, 2.0], [4.0, 5.0], [1.5, 2.5], [4.2, 5.1]], dtype=float),
                xlim=[0, 4],
                ylim=[0, 6],
            ),
        ]
    )


def _fmt(values):
    parts = []
    for value in np.asarray(values, dtype=float).reshape(-1):
        if not np.isfinite(value):
            parts.append("NA")
        else:
            parts.append("%.17g" % float(value))
    return ",".join(parts)


drawn = plotGrowthCurves(curve_group(), curves(), times=[1, 2, 4], col=[2, 4, "darkgreen"])
drawn["figure"].savefig(OUT / "plotGrowthCurves-python.svg", format="svg", bbox_inches="tight")
plt.close(drawn["figure"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)
print(_fmt(value))
print("MS")
print("%.17g" % statistics.median(elapsed))
