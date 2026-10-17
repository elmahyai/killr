"""Index of the polygon with the greatest coverage in each cell."""

from __future__ import annotations

import numpy as np

from ._grid import as_features, parse_grid
from ._intersect import raster_cell_intersection


def rasterize_polygons(x, y, min_coverage: float = 0) -> dict:
    """Write the 1-based index of the polygon in ``x`` that covers each cell of ``y`` most.

    Ties keep the lowest index. Cells whose total coverage is below
    ``min_coverage`` are missing. ``min_coverage`` of 1 is eased by 1e-6,
    matching ``R/rasterize.R``.
    """
    grid, _values = parse_grid(y)
    features = as_features(x)
    if min_coverage == 1.0:
        min_coverage = min_coverage - 1e-6

    max_cov = np.zeros((grid.rows, grid.cols), dtype=np.float64)
    tot = np.zeros((grid.rows, grid.cols), dtype=np.float64)
    index = [[None for _ in range(grid.cols)] for _ in range(grid.rows)]

    for feature_index, wkt in enumerate(features, start=1):
        cov, cov_grid = raster_cell_intersection(grid, wkt)
        if cov_grid.empty() or cov.size == 0:
            continue
        ix = grid.row_offset(cov_grid)
        jx = grid.col_offset(cov_grid)
        for i in range(cov.shape[0]):
            for j in range(cov.shape[1]):
                covered = float(cov[i, j])
                if covered > 0.0:
                    tot[i + ix, j + jx] += covered
                    if covered > max_cov[i + ix, j + jx]:
                        max_cov[i + ix, j + jx] = covered
                        index[i + ix][j + jx] = feature_index

    for i in range(grid.rows):
        for j in range(grid.cols):
            if tot[i, j] < min_coverage:
                index[i][j] = None

    return {
        "values": index,
        "xmin": grid.xmin,
        "xmax": grid.xmax,
        "ymin": grid.ymin,
        "ymax": grid.ymax,
    }
