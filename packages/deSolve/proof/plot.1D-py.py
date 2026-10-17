import importlib.util
import json
import statistics
import time

import matplotlib.pyplot as plt
import numpy as np

_spec = importlib.util.spec_from_file_location(
    "plot_1d",
    "/home/ahmed/killr_projects/killr/packages/deSolve/deSolve/plot_1d.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
plot_1d = _mod.plot_1d


class Series:
    def __init__(self, data, colnames, lengthvar, lengthvar_names):
        self.data = data
        self.colnames = colnames
        self.istate = None
        self.lengthvar = lengthvar
        self.lengthvar_names = lengthvar_names
        self.dimens = 4
        self.nspec = 1
        self.ynames = ["Aphid"]


def make_series(shift):
    mat = np.array(
        [
            [0.0, 1.0, 1.2, 1.4, 1.1, 0.10, 0.20, 0.00, -0.10, 0.30],
            [0.5, 1.1, 1.3, 1.5, 1.2, 0.20, 0.10, 0.10, -0.20, 0.20],
            [1.0, 1.3, 1.1, 1.6, 1.4, 0.00, 0.30, 0.20, 0.10, 0.00],
            [1.5, 1.4, 1.5, 1.2, 1.3, 0.40, 0.20, -0.10, 0.20, 0.10],
        ],
        dtype=np.float64,
    )
    mat[:, 1:] = mat[:, 1:] + shift
    return Series(
        mat,
        ["time", "A1", "A2", "A3", "A4", "F1", "F2", "F3", "F4", "F5"],
        [4, 5],
        ["", "Flux"],
    )


class Obs:
    def __init__(self, data, colnames):
        self.data = data
        self.colnames = colnames


mat = make_series(0.0)
mat2 = make_series(0.25)
obs = Obs(
    np.array([[0.0, 0.9, 0.5], [2.0, 1.7, -0.4]], dtype=np.float64),
    ["x", "Aphid", "Flux"],
)
grid = ([0.0, 1.0, 2.0, 3.0], [0.0, 0.5, 1.0, 1.5, 2.0])


def flatten(drawn):
    values = []
    for panel in drawn.panels:
        if panel.get("empty"):
            continue
        values.extend(float(v) for v in panel["x"])
        values.extend(float(v) for v in panel["y"])
        xlim = panel["xlim"]
        ylim = panel["ylim"]
        if xlim is None:
            pass
        else:
            values.extend([float(xlim[0]), float(xlim[1])])
        if ylim is None:
            pass
        else:
            values.extend([float(ylim[0]), float(ylim[1])])
        for line in panel["lines"]:
            values.extend(float(v) for v in line["x"])
            values.extend(float(v) for v in line["y"])
            values.extend([])  # xlim ylim placeholders stay absent, matching a numeric(0) pair only if we add nothing
        for point in panel["points"]:
            values.extend(float(v) for v in point["x"])
            values.extend(float(v) for v in point["y"])
    return values


def draw():
    return plot_1d(
        mat,
        mat2,
        which=["Aphid", "Flux"],
        type="l",
        ask=False,
        xyswap=True,
        grid=grid,
        subset=[1, 3],
        lwd=2,
        col=["red", "blue"],
        obs=obs,
    )


def one():
    drawn = draw()
    values = flatten(drawn)
    if drawn.figure is not None:
        plt.close(drawn.figure)
    return values


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

drawn = plot_1d(mat, type="l", lwd=2, xyswap=True, ask=False)
drawn.figure.savefig(
    "/home/ahmed/killr_projects/killr/packages/deSolve/docs/output/plot.1D-python.svg",
    format="svg",
)
plt.close(drawn.figure)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
