"""Fraction of each cell covered by a polygon."""

from __future__ import annotations

import numpy as np

from ._grid import as_features, extent_dict, matrix_to_lists, parse_grid, view_raster
from ._intersect import raster_cell_intersection


def coverage_fraction(x, y, crop: bool = False) -> list[dict]:
    """Coverage of each cell of grid ``x`` by polygon ``y``.

    ``y`` is a WKT string or a list of WKT strings, one feature each.
    ``crop=False`` keeps the input grid and writes 0 outside the polygon.
    ``crop=True`` returns the cells the C++ intersection processed.
    """
    grid, _values = parse_grid(x)
    out = []
    for wkt in as_features(y):
        cov, cov_grid = raster_cell_intersection(grid, wkt)
        if crop:
            out.append(extent_dict(cov_grid, matrix_to_lists(cov)))
        else:
            viewed = view_raster(cov, cov_grid, grid)
            viewed = np.where(np.isnan(viewed), 0.0, viewed).astype(np.float64)
            out.append(extent_dict(grid, matrix_to_lists(viewed)))
    return out
