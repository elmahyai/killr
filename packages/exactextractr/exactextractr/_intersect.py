"""Raster cell intersection.

This is ``raster_cell_intersection.cpp`` and ``floodfill.cpp``. Coverage is
stored as ``float32``, matching ``Matrix<float>``.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from ._cell import Cell, Coordinate, area, length
from ._geos import (
    GEOS_GEOMETRYCOLLECTION,
    GEOS_LINEARRING,
    GEOS_LINESTRING,
    GEOS_MULTILINESTRING,
    GEOS_MULTIPOLYGON,
    GEOS_POLYGON,
    Context,
    Geom,
    Prepared,
    geos,
)
from ._grid import (
    SIDE_BOTTOM,
    SIDE_LEFT,
    SIDE_RIGHT,
    SIDE_TOP,
    Box,
    Grid,
    grid_cell,
    make_finite,
    make_infinite,
)

_FILLABLE = np.float32(-1.0)
_INTERIOR = np.float32(1.0)
_EXTERIOR = np.float32(0.0)
_UNKNOWN = np.float32(-2.0)
_PAD = 1


def processing_region(raster_extent: Box, component_boxes: list[Box]) -> Box:
    ret = Box.make_empty()
    for box in component_boxes:
        if ret == raster_extent:
            return ret
        if not box.intersects(raster_extent):
            continue
        isect = raster_extent.intersection(box)
        if ret.empty():
            ret = isect
        elif not ret.contains_box(isect):
            ret = ret.expand_to_include(isect)
    return ret


def _geometry_grid(raster_grid: Grid, ctx: Context, geom: Geom) -> Grid:
    if ctx.is_empty(geom):
        raise ValueError("Can't get statistics for empty geometry")
    region = processing_region(raster_grid.extent, ctx.component_boxes(geom))
    if not region.empty():
        return make_infinite(raster_grid.shrink_to_fit(region))
    return Grid.make_empty(padding=_PAD)


def _box_grid(raster_grid: Grid, box: Box) -> Grid:
    region = box.intersection(raster_grid.extent)
    if not region.empty():
        return make_infinite(raster_grid.shrink_to_fit(region))
    return Grid.make_empty(padding=_PAD)


def _subgrid_for_box(box: Box, geometry_grid: Grid) -> Grid:
    cropped = geometry_grid.extent.intersection(box)
    return geometry_grid.shrink_to_fit(cropped)


class _FloodFill:
    def __init__(self, ctx: Context, ring: Geom, extent: Grid) -> None:
        self.extent = extent
        self.prepared: Prepared = ctx.prepare_ring(ring)

    def cell_is_inside(self, i: int, j: int) -> bool:
        x = self.extent.x_for_col(j)
        y = self.extent.y_for_row(i)
        return self.prepared.contains(x, y)

    def flood(self, arr: np.ndarray) -> None:
        rows, cols = arr.shape
        for i in range(rows):
            for j in range(cols):
                if arr[i, j] == _UNKNOWN:
                    raise RuntimeError("Cell with unknown position encountered.")
                if arr[i, j] == _FILLABLE:
                    fill = _INTERIOR if self.cell_is_inside(i, j) else _EXTERIOR
                    _flood_from_pixel(arr, i, j, fill)

    def close(self) -> None:
        self.prepared.close()


def _flood_from_pixel(arr: np.ndarray, i: int, j: int, fill_value: np.float32) -> None:
    locations: deque[tuple[int, int]] = deque()
    locations.append((i, j))
    rows, cols = arr.shape
    while locations:
        i, j = locations.popleft()
        if arr[i, j] == fill_value:
            continue
        if j > 0 and arr[i, j - 1] == _FILLABLE:
            locations.append((i, j - 1))
        j0 = j
        while j < cols and arr[i, j] == _FILLABLE:
            arr[i, j] = fill_value
            j += 1
        j1 = j
        if i > 0:
            for jj in range(j0, j1):
                if arr[i - 1, jj] == _FILLABLE:
                    locations.append((i - 1, jj))
        if i < rows - 1:
            for jj in range(j0, j1):
                if arr[i + 1, jj] == _FILLABLE:
                    locations.append((i + 1, jj))


def _get_cell(cells: list[list[Cell | None]], grid: Grid, row: int, col: int) -> Cell:
    if cells[row][col] is None:
        cells[row][col] = Cell(grid_cell(grid, row, col))
    cell = cells[row][col]
    assert cell is not None
    return cell


class RasterCellIntersection:
    def __init__(self, geometry_grid: Grid) -> None:
        self.geometry_grid = geometry_grid
        rows = max(geometry_grid.rows - 2, 0)
        cols = max(geometry_grid.cols - 2, 0)
        self.results = np.zeros((rows, cols), dtype=np.float32)
        self._first = True
        self._areal = False

    def set_areal(self, areal: bool) -> None:
        if self._first:
            self._first = False
            self._areal = areal
        elif self._areal != areal:
            raise RuntimeError("Mixed-type geometries not supported.")

    def process(self, ctx: Context, geom: Geom) -> None:
        kind = ctx.type_id(geom)
        if kind == GEOS_POLYGON:
            self.set_areal(True)
            self.process_line(ctx, ctx.exterior_ring(geom), True)
            for i in range(ctx.num_interior_rings(geom)):
                self.process_line(ctx, ctx.interior_ring(geom, i), False)
        elif kind in (GEOS_LINESTRING, GEOS_LINEARRING):
            self.set_areal(False)
            self.process_line(ctx, geom, True)
        elif kind in (GEOS_GEOMETRYCOLLECTION, GEOS_MULTILINESTRING, GEOS_MULTIPOLYGON):
            for i in range(ctx.num_geometries(geom)):
                self.process(ctx, ctx.geometry_n(geom, i))
        else:
            raise ValueError("Unsupported geometry type.")

    def process_rectangular_ring(self, box: Box, exterior_ring: bool) -> None:
        if not box.intersects(self.geometry_grid.extent):
            return
        ring_grid = _subgrid_for_box(box, self.geometry_grid)
        row_min = ring_grid.get_row(box.ymax)
        row_max = ring_grid.get_row(box.ymin)
        col_min = ring_grid.get_column(box.xmin)
        col_max = ring_grid.get_column(box.xmax)
        areas = np.zeros((ring_grid.rows - 2, ring_grid.cols - 2), dtype=np.float32)

        if row_min > 0 and col_min > 0:
            ul = grid_cell(ring_grid, row_min, col_min)
            areas[row_min - 1, col_min - 1] = np.float32(ul.intersection(box).area() / ul.area())
        if row_min > 0 and col_max < ring_grid.cols - 1:
            ur = grid_cell(ring_grid, row_min, col_max)
            areas[row_min - 1, col_max - 1] = np.float32(ur.intersection(box).area() / ur.area())
        if row_max < ring_grid.rows - 1 and col_min > 0:
            ll = grid_cell(ring_grid, row_max, col_min)
            areas[row_max - 1, col_min - 1] = np.float32(ll.intersection(box).area() / ll.area())
        if row_max < ring_grid.rows - 1 and col_max < ring_grid.cols - 1:
            lr = grid_cell(ring_grid, row_max, col_max)
            areas[row_max - 1, col_max - 1] = np.float32(lr.intersection(box).area() / lr.area())

        if col_min > 0:
            left = grid_cell(ring_grid, row_min + 1, col_min)
            frac = np.float32(left.intersection(box).area() / left.area())
            for row in range(row_min + 1, row_max):
                areas[row - 1, col_min - 1] = frac
        if col_max < ring_grid.cols - 1:
            right = grid_cell(ring_grid, row_min + 1, col_max)
            frac = np.float32(right.intersection(box).area() / right.area())
            for row in range(row_min + 1, row_max):
                areas[row - 1, col_max - 1] = frac
        if row_min > 0:
            top = grid_cell(ring_grid, row_min, col_min + 1)
            frac = np.float32(top.intersection(box).area() / top.area())
            for col in range(col_min + 1, col_max):
                areas[row_min - 1, col - 1] = frac
        if row_max < ring_grid.rows - 1:
            bottom = grid_cell(ring_grid, row_max, col_min + 1)
            frac = np.float32(bottom.intersection(box).area() / bottom.area())
            for col in range(col_min + 1, col_max):
                areas[row_max - 1, col - 1] = frac

        for row in range(row_min + 1, row_max):
            for col in range(col_min + 1, col_max):
                areas[row - 1, col - 1] = np.float32(1.0)

        self._add_ring_results(
            ring_grid.row_offset(self.geometry_grid),
            ring_grid.col_offset(self.geometry_grid),
            areas,
            exterior_ring,
        )

    def process_line(self, ctx: Context, line: Geom, exterior_ring: bool) -> None:
        geom_box = ctx.box(line)
        if not geom_box.intersects(self.geometry_grid.extent):
            return
        coords = [Coordinate(x, y) for x, y in ctx.read_coords(line)]
        if self._areal and len(coords) == 5 and area(coords) == geom_box.area():
            self.process_rectangular_ring(geom_box, exterior_ring)
            return

        ring_grid = _subgrid_for_box(geom_box, self.geometry_grid)
        rows = ring_grid.rows
        cols = ring_grid.cols
        if (
            rows == (1 + 2 * _PAD)
            and cols == (1 + 2 * _PAD)
            and grid_cell(ring_grid, 1, 1).contains_box(geom_box)
        ):
            i0 = ring_grid.row_offset(self.geometry_grid)
            j0 = ring_grid.col_offset(self.geometry_grid)
            if self._areal:
                ring_area = area(coords) / grid_cell(ring_grid, 1, 1).area()
                delta = ring_area if exterior_ring else -ring_area
                self.results[i0, j0] = np.float32(self.results[i0, j0] + np.float32(delta))
            else:
                self.results[i0, j0] = np.float32(self.results[i0, j0] + np.float32(length(coords)))
            return

        cells: list[list[Cell | None]] = [[None for _ in range(cols)] for _ in range(rows)]
        if self._areal and not ctx.is_ccw(line):
            coords.reverse()

        pos = 0
        row = ring_grid.get_row(coords[0].y)
        col = ring_grid.get_column(coords[0].x)
        last_exit: Coordinate | None = None

        while pos < len(coords):
            cell = _get_cell(cells, ring_grid, row, col)
            while pos < len(coords):
                next_coord = last_exit if last_exit is not None else coords[pos]
                prev_coord = coords[pos - 1] if pos > 0 else None
                cell.take(next_coord, prev_coord)
                if cell.last_traversal().exited():
                    exc = cell.last_traversal().exit_coordinate()
                    if exc != next_coord:
                        last_exit = Coordinate(exc.x, exc.y)
                    break
                if last_exit is not None:
                    last_exit = None
                else:
                    pos += 1

            cell.force_exit()
            if cell.last_traversal().exited():
                if self._areal and not cell.last_traversal().traversed():
                    for coord in cell.last_traversal().coords:
                        coords.append(Coordinate(coord.x, coord.y))
                side = cell.last_traversal().exit_side
                if side == SIDE_TOP:
                    row -= 1
                elif side == SIDE_BOTTOM:
                    row += 1
                elif side == SIDE_LEFT:
                    col -= 1
                elif side == SIDE_RIGHT:
                    col += 1
                else:
                    raise RuntimeError("Invalid traversal")

        fill_value = _FILLABLE if self._areal else _EXTERIOR
        areas = np.full((rows - 2, cols - 2), fill_value, dtype=np.float32)
        if self._areal:
            flood = _FloodFill(ctx, line, make_finite(ring_grid))
            try:
                for i in range(1, areas.shape[0] + 1):
                    for j in range(1, areas.shape[1] + 1):
                        if cells[i][j] is not None:
                            frac = np.float32(cells[i][j].covered_fraction())
                            if frac == 0:
                                areas[i - 1, j - 1] = (
                                    _INTERIOR if flood.cell_is_inside(i - 1, j - 1) else _EXTERIOR
                                )
                            else:
                                areas[i - 1, j - 1] = frac
                flood.flood(areas)
            finally:
                flood.close()
        else:
            for i in range(1, areas.shape[0] + 1):
                for j in range(1, areas.shape[1] + 1):
                    if cells[i][j] is not None:
                        areas[i - 1, j - 1] = np.float32(cells[i][j].traversal_length())

        self._add_ring_results(
            ring_grid.row_offset(self.geometry_grid),
            ring_grid.col_offset(self.geometry_grid),
            areas,
            exterior_ring or not self._areal,
        )

    def _add_ring_results(self, i0: int, j0: int, areas: np.ndarray, exterior_ring: bool) -> None:
        factor = np.float32(1.0 if exterior_ring else -1.0)
        for i in range(areas.shape[0]):
            for j in range(areas.shape[1]):
                self.results[i0 + i, j0 + j] = np.float32(
                    self.results[i0 + i, j0 + j] + factor * areas[i, j]
                )


def raster_cell_intersection(raster_grid: Grid, wkt: str) -> tuple[np.ndarray, Grid]:
    ctx = geos()
    geom = ctx.from_wkt(wkt)
    try:
        if ctx.dimensions(geom) == 0:
            raise ValueError("Unsupported geometry type.")
        geometry_grid = _geometry_grid(raster_grid, ctx, geom)
        rci = RasterCellIntersection(geometry_grid)
        if not geometry_grid.empty():
            rci.process(ctx, geom)
        return rci.results, make_finite(geometry_grid)
    finally:
        geom.close()


def raster_cell_intersection_box(raster_grid: Grid, box: Box) -> tuple[np.ndarray, Grid]:
    geometry_grid = _box_grid(raster_grid, box)
    rci = RasterCellIntersection(geometry_grid)
    if not geometry_grid.empty():
        rci.process_rectangular_ring(box, True)
    return rci.results, make_finite(geometry_grid)


def cartesian_cell_area(grid: Grid) -> float:
    if grid.rows == 0 or grid.cols == 0:
        return 0.0
    return grid_cell(grid, 0, 0).area()
