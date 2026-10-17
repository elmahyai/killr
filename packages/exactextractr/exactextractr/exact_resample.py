"""Resample one grid onto another by cell coverage."""

from __future__ import annotations

import numpy as np

from ._grid import extent_dict, grid_cell, parse_grid, view_raster
from ._intersect import cartesian_cell_area, raster_cell_intersection_box
from .exact_extract import RasterStats, stat_value


def exact_resample(x, y, fun: str = "mean", coverage_area: bool = False) -> dict:
    """Resample grid ``x`` onto the grid of ``y``.

    ``fun`` is one summary name. Weighted summaries are not used for resampling.
    The result uses ``y``'s extent.
    """
    if not isinstance(fun, str):
        raise ValueError("Only a single operation may be used for resampling.")
    if fun.startswith("weighted"):
        raise ValueError("Weighted operations cannot be used for resampling.")

    src_grid, values = parse_grid(x)
    if values is None:
        raise ValueError("exact_resample requires values on the source grid")
    dst_grid, _dst_values = parse_grid(y)
    store = fun in ("mode", "majority", "minority", "variety", "median")
    out = []
    for row in range(dst_grid.rows):
        line = []
        for col in range(dst_grid.cols):
            cell = grid_cell(dst_grid, row, col)
            cov, cov_grid = raster_cell_intersection_box(src_grid, cell)
            if coverage_area and cov.size and not cov_grid.empty():
                area = cartesian_cell_area(cov_grid)
                cov = np.float32(cov.astype(np.float64) * area)
            stats = RasterStats(store)
            if cov.size and not cov_grid.empty():
                viewed = view_raster(values, src_grid, cov_grid)
                stats.process(cov, viewed, None)
            line.append(stat_value(stats, fun))
        out.append(line)
    return extent_dict(dst_grid, out)
