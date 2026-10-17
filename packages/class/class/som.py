"""Self-organizing maps from class.

somgrid and batchSOM are the R routines. The online map is VR_onlineSOM.
A supplied initial codebook skips the random start. The online pass draws
with boot's unif, matching R's unif_rand.
"""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

_knn = importlib.import_module("class.knn")
_rows = _knn._rows
knn1 = _knn.knn1


def _rng():
    try:
        from boot import rng as module
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot import rng as module
    return module


def somgrid(xdim=8, ydim=6, topo="rectangular"):
    """Grid points. x varies fastest. Hexagonal rows are staggered."""
    kind = str(topo).lower()
    if kind not in {"rectangular", "hexagonal"}:
        raise ValueError("topo must be rectangular or hexagonal")
    pts = []
    for y in range(1, int(ydim) + 1):
        for x in range(1, int(xdim) + 1):
            pts.append([float(x), float(y)])
    if kind == "hexagonal":
        for point in pts:
            point[0] += 0.5 * (int(point[1]) % 2)
            point[1] = math.sqrt(3) / 2 * point[1]
    return {"pts": pts, "xdim": int(xdim), "ydim": int(ydim), "topo": kind}


def _euclid(left, right):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _grid_dist(pts):
    return [[_euclid(a, b) for b in pts] for a in pts]


def batchSOM(data, grid=None, radii=None, init=None):
    """Batch map. Each radius replaces a code by the mean of its neighborhood."""
    rows = _rows(data)
    if grid is None:
        grid = somgrid()
    if radii is None:
        raise ValueError("radii is required")
    codes = [list(row) for row in rows[: len(grid["pts"])]] if init is None else [list(row) for row in _rows(init)]
    if init is None:
        picks = _rng().sample_int(len(rows), len(grid["pts"]), replace=False)
        codes = [list(rows[index - 1]) for index in picks]
    neighbors = _grid_dist(grid["pts"])
    labels = list(range(1, len(codes) + 1))
    for radius in radii:
        assigned = [int(label) - 1 for label in knn1(codes, rows, labels)]
        for index, code_neighbors in enumerate(neighbors):
            chosen = [row for row, owner in zip(rows, assigned) if code_neighbors[owner] <= radius]
            if chosen:
                width = len(chosen[0])
                codes[index] = [sum(row[col] for row in chosen) / len(chosen) for col in range(width)]
    return {"grid": grid, "codes": codes}


def _online(data, codes, neighbors, alpha, radii):
    """One phase of VR_onlineSOM. Search every code, then move the neighborhood."""
    n = len(data)
    generator = _rng()
    for rate, radius in zip(alpha, radii):
        i = int(n * generator.unif())
        point = data[i]
        best = float("inf")
        nearest = 0
        nind = 1
        for index, code in enumerate(codes):
            gap = sum((a - b) ** 2 for a, b in zip(point, code))
            if gap <= best * (1 + 1e-4):
                if gap < best * (1 - 1e-4):
                    nind = 1
                    nearest = index
                else:
                    nind += 1
                    if nind * generator.unif() < 1.0:
                        nearest = index
                best = gap
        for index, code in enumerate(codes):
            if neighbors[index][nearest] > radius:
                continue
            codes[index] = [value + rate * (src - value) for value, src in zip(code, point)]
    return codes


def SOM(data, grid=None, rlen=10000, alpha=None, radii=None, init=None):
    """Online map. alpha and radii are one list, or a list of phases."""
    rows = _rows(data)
    if not rows:
        raise ValueError("'SOM' called with no data")
    if grid is None:
        grid = somgrid()
    if alpha is None:
        alpha = [0.05 * (1 - step / (rlen - 1 if rlen > 1 else 1)) for step in range(int(rlen))]
    if radii is None:
        radii = [4 - 3 * step / (rlen - 1 if rlen > 1 else 1) for step in range(int(rlen))]
    phases_a = alpha if alpha and isinstance(alpha[0], (list, tuple)) else [alpha]
    phases_r = radii if radii and isinstance(radii[0], (list, tuple)) else [radii]
    if len(phases_a) != len(phases_r):
        raise ValueError("'radii' must be a list of the same length as 'alpha'")
    if init is None:
        picks = _rng().sample_int(len(rows), len(grid["pts"]), replace=False)
        codes = [list(rows[index - 1]) for index in picks]
    else:
        codes = [list(row) for row in _rows(init)]
    neighbors = _grid_dist(grid["pts"])
    for phase_alpha, phase_radii in zip(phases_a, phases_r):
        if len(phase_alpha) != len(phase_radii):
            raise ValueError("'alpha' and 'radii' do not have the same lengths")
        codes = _online(rows, codes, neighbors, phase_alpha, phase_radii)
    return {"grid": grid, "codes": codes}
