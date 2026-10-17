"""Grid, box, and cell geometry from exactextract.

The walk follows ``grid.h``, ``grid.cpp``, and ``box.cpp``. A bounded grid
has no padding. An infinite grid adds one cell of padding on every side.
"""

from __future__ import annotations

import math
import sys

import numpy as np

_DBL_MAX = sys.float_info.max
_DBL_LOWEST = -sys.float_info.max


def cpp_round(x: float) -> int:
    """``std::round``: halfway cases go away from zero."""
    if x >= 0.0:
        return int(math.floor(x + 0.5))
    return int(math.ceil(x - 0.5))


def _is_integral(d: float, tol: float) -> bool:
    return abs(d - cpp_round(d)) <= tol


class Box:
    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    @staticmethod
    def make_empty() -> "Box":
        return Box(0.0, 0.0, 0.0, 0.0)

    def width(self) -> float:
        return self.xmax - self.xmin

    def height(self) -> float:
        return self.ymax - self.ymin

    def area(self) -> float:
        return self.width() * self.height()

    def perimeter(self) -> float:
        return 2.0 * self.width() + 2.0 * self.height()

    def empty(self) -> bool:
        return self.xmin >= self.xmax or self.ymin >= self.ymax

    def intersects(self, other: "Box") -> bool:
        if other.ymin > self.ymax:
            return False
        if other.ymax < self.ymin:
            return False
        if other.xmin > self.xmax:
            return False
        if other.xmax < self.xmin:
            return False
        return True

    def intersection(self, other: "Box") -> "Box":
        return Box(
            max(self.xmin, other.xmin),
            max(self.ymin, other.ymin),
            min(self.xmax, other.xmax),
            min(self.ymax, other.ymax),
        )

    def contains_box(self, other: "Box") -> bool:
        return (
            other.xmin >= self.xmin
            and other.xmax <= self.xmax
            and other.ymin >= self.ymin
            and other.ymax <= self.ymax
        )

    def contains_coord(self, x: float, y: float) -> bool:
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

    def strictly_contains(self, x: float, y: float) -> bool:
        return self.xmin < x < self.xmax and self.ymin < y < self.ymax

    def expand_to_include(self, other: "Box") -> "Box":
        if self.empty():
            return other
        if other.empty():
            return self
        return Box(
            min(self.xmin, other.xmin),
            min(self.ymin, other.ymin),
            max(self.xmax, other.xmax),
            max(self.ymax, other.ymax),
        )

    def side(self, x: float, y: float) -> int:
        if x == self.xmin:
            return SIDE_LEFT
        if x == self.xmax:
            return SIDE_RIGHT
        if y == self.ymin:
            return SIDE_BOTTOM
        if y == self.ymax:
            return SIDE_TOP
        return SIDE_NONE

    def crossing(self, x1: float, y1: float, x2: float, y2: float) -> tuple[int, float, float]:
        if x1 == x2:
            if y2 >= self.ymax:
                return SIDE_TOP, x1, self.ymax
            if y2 <= self.ymin:
                return SIDE_BOTTOM, x1, self.ymin
            raise RuntimeError("Never get here.")
        if y1 == y2:
            if x2 >= self.xmax:
                return SIDE_RIGHT, self.xmax, y1
            if x2 <= self.xmin:
                return SIDE_LEFT, self.xmin, y1
            raise RuntimeError("Never get here")

        slope = abs((y2 - y1) / (x2 - x1))
        up = y2 > y1
        right = x2 > x1

        if up:
            if right:
                y_hit = y1 + slope * (self.xmax - x1)
                if y_hit < self.ymax:
                    return SIDE_RIGHT, self.xmax, _clamp(y_hit, self.ymin, self.ymax)
                x_hit = x1 + (self.ymax - y1) / slope
                return SIDE_TOP, _clamp(x_hit, self.xmin, self.xmax), self.ymax
            y_hit = y1 + slope * (x1 - self.xmin)
            if y_hit < self.ymax:
                return SIDE_LEFT, self.xmin, _clamp(y_hit, self.ymin, self.ymax)
            x_hit = x1 - (self.ymax - y1) / slope
            return SIDE_TOP, _clamp(x_hit, self.xmin, self.xmax), self.ymax

        if right:
            y_hit = y1 - slope * (self.xmax - x1)
            if y_hit > self.ymin:
                return SIDE_RIGHT, self.xmax, _clamp(y_hit, self.ymin, self.ymax)
            x_hit = x1 + (y1 - self.ymin) / slope
            return SIDE_BOTTOM, _clamp(x_hit, self.xmin, self.xmax), self.ymin

        y_hit = y1 - slope * (x1 - self.xmin)
        if y_hit > self.ymin:
            return SIDE_LEFT, self.xmin, _clamp(y_hit, self.ymin, self.ymax)
        x_hit = x1 - (y1 - self.ymin) / slope
        return SIDE_BOTTOM, _clamp(x_hit, self.xmin, self.xmax), self.ymin

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Box):
            return NotImplemented
        return (
            self.xmin == other.xmin
            and self.xmax == other.xmax
            and self.ymin == other.ymin
            and self.ymax == other.ymax
        )


def _clamp(x: float, low: float, high: float) -> float:
    return min(max(x, low), high)


SIDE_NONE = 0
SIDE_LEFT = 1
SIDE_RIGHT = 2
SIDE_TOP = 3
SIDE_BOTTOM = 4


class Grid:
    def __init__(self, extent: Box, dx: float, dy: float, padding: int = 0) -> None:
        self.extent = extent
        self.dx = float(dx)
        self.dy = float(dy)
        self.padding = padding
        if extent.ymax > extent.ymin and self.dy != 0.0:
            self.num_rows = 2 * padding + cpp_round((extent.ymax - extent.ymin) / self.dy)
        else:
            self.num_rows = 2 * padding
        if extent.xmax > extent.xmin and self.dx != 0.0:
            self.num_cols = 2 * padding + cpp_round((extent.xmax - extent.xmin) / self.dx)
        else:
            self.num_cols = 2 * padding

    @staticmethod
    def make_empty(padding: int = 0) -> "Grid":
        return Grid(Box.make_empty(), 0.0, 0.0, padding)

    @property
    def rows(self) -> int:
        return self.num_rows

    @property
    def cols(self) -> int:
        return self.num_cols

    @property
    def xmin(self) -> float:
        return self.extent.xmin

    @property
    def xmax(self) -> float:
        return self.extent.xmax

    @property
    def ymin(self) -> float:
        return self.extent.ymin

    @property
    def ymax(self) -> float:
        return self.extent.ymax

    def empty(self) -> bool:
        return self.num_rows <= 2 * self.padding and self.num_cols <= 2 * self.padding

    def get_column(self, x: float) -> int:
        if self.padding:
            if x < self.extent.xmin:
                return 0
            if x > self.extent.xmax:
                return self.num_cols - 1
            if x == self.extent.xmax:
                return self.num_cols - 2
            cap = self.num_cols - 2
        else:
            if x < self.extent.xmin or x > self.extent.xmax:
                raise IndexError("x")
            if x == self.extent.xmax:
                return self.num_cols - 1
            cap = self.num_cols - 1
        raw = self.padding + int(math.floor((x - self.extent.xmin) / self.dx))
        return min(raw, cap)

    def get_row(self, y: float) -> int:
        if self.padding:
            if y > self.extent.ymax:
                return 0
            if y < self.extent.ymin:
                return self.num_rows - 1
            if y == self.extent.ymin:
                return self.num_rows - 2
            cap = self.num_rows - 2
        else:
            if y < self.extent.ymin or y > self.extent.ymax:
                raise IndexError("y")
            if y == self.extent.ymin:
                return self.num_rows - 1
            cap = self.num_rows - 1
        raw = self.padding + int(math.floor((self.extent.ymax - y) / self.dy))
        return min(raw, cap)

    def row_offset(self, other: "Grid") -> int:
        return cpp_round(abs(other.extent.ymax - self.extent.ymax) / self.dy)

    def col_offset(self, other: "Grid") -> int:
        return cpp_round(abs(self.extent.xmin - other.extent.xmin) / self.dx)

    def x_for_col(self, col: int) -> float:
        return self.extent.xmin + ((col - self.padding) + 0.5) * self.dx

    def y_for_row(self, row: int) -> float:
        return self.extent.ymax - ((row - self.padding) + 0.5) * self.dy

    def crop(self, box: Box) -> "Grid":
        if self.extent.intersects(box):
            return self.shrink_to_fit(box.intersection(self.extent))
        return Grid.make_empty(self.padding)

    def shrink_to_fit(self, box: Box) -> "Grid":
        if (
            box.xmin < self.extent.xmin
            or box.ymin < self.extent.ymin
            or box.xmax > self.extent.xmax
            or box.ymax > self.extent.ymax
        ):
            raise ValueError("Cannot shrink extent to bounds larger than original.")

        col0 = self.get_column(box.xmin)
        row1 = self.get_row(box.ymax)
        snapped_xmin = self.extent.xmin + (col0 - self.padding) * self.dx
        snapped_ymax = self.extent.ymax - (row1 - self.padding) * self.dy

        if box.xmin < snapped_xmin:
            snapped_xmin -= self.dx
            col0 -= 1
        if box.ymax > snapped_ymax:
            snapped_ymax += self.dy
            row1 -= 1

        col1 = self.get_column(box.xmax)
        row0 = self.get_row(box.ymin)
        num_rows = 1 + (row0 - row1)
        num_cols = 1 + (col1 - col0)

        if num_rows > 2 and (snapped_ymax - (num_rows - 1) * self.dy <= box.ymin):
            num_rows -= 1
        if num_cols > 2 and (snapped_xmin + (num_cols - 1) * self.dx >= box.xmax):
            num_cols -= 1

        reduced = Box(
            snapped_xmin,
            min(snapped_ymax - num_rows * self.dy, box.ymin),
            max(snapped_xmin + num_cols * self.dx, box.xmax),
            snapped_ymax,
        )

        if reduced.xmax > self.extent.xmax:
            if cpp_round((reduced.xmax - reduced.xmin) / self.dx) == cpp_round(
                (self.extent.xmax - reduced.xmin) / self.dx
            ):
                reduced.xmax = self.extent.xmax
            else:
                raise RuntimeError("Shrink operation failed.")
        if reduced.ymin < self.extent.ymin:
            if cpp_round((reduced.ymax - reduced.ymin) / self.dy) == cpp_round(
                (reduced.ymax - self.extent.ymin) / self.dy
            ):
                reduced.ymin = self.extent.ymin
            else:
                raise RuntimeError("Shrink operation failed.")

        out = Grid(reduced, self.dx, self.dy, self.padding)
        if box.xmin < out.xmin or box.ymin < out.ymin or box.xmax > out.xmax or box.ymax > out.ymax:
            raise RuntimeError("Shrink operation failed.")
        return out

    def compatible_with(self, other: "Grid", tol: float) -> bool:
        if self.empty() or other.empty():
            return True
        xtol = min(self.dx, other.dx) * tol
        ytol = min(self.dy, other.dy) * tol
        if not _is_integral(max(self.dx, other.dx) / min(self.dx, other.dx), xtol):
            return False
        if not _is_integral(max(self.dy, other.dy) / min(self.dy, other.dy), ytol):
            return False
        if not _is_integral(abs(other.extent.xmin - self.extent.xmin) / min(self.dx, other.dx), xtol):
            return False
        if not _is_integral(abs(other.extent.ymax - self.extent.ymax) / min(self.dy, other.dy), ytol):
            return False
        return True

    def common_grid(self, other: "Grid", tol: float = 1e-6) -> "Grid":
        if not self.compatible_with(other, tol):
            raise RuntimeError("Incompatible extents.")
        if other.empty():
            return self
        common_dx = min(self.dx, other.dx)
        common_dy = min(self.dy, other.dy)
        common_xmin = min(self.extent.xmin, other.extent.xmin)
        common_ymax = max(self.extent.ymax, other.extent.ymax)
        common_xmax = max(self.extent.xmax, other.extent.xmax)
        common_ymin = min(self.extent.ymin, other.extent.ymin)
        nx = cpp_round((common_xmax - common_xmin) / common_dx)
        ny = cpp_round((common_ymax - common_ymin) / common_dy)
        common_xmax = max(common_xmax, common_xmin + nx * common_dx)
        common_ymin = min(common_ymin, common_ymax - ny * common_dy)
        return Grid(Box(common_xmin, common_ymin, common_xmax, common_ymax), common_dx, common_dy, self.padding)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Grid):
            return NotImplemented
        return self.extent == other.extent and self.dx == other.dx and self.dy == other.dy


def grid_cell(grid: Grid, row: int, col: int) -> Box:
    if grid.padding == 0:
        xmin = grid.xmin + col * grid.dx
        ymin = grid.ymin if row == (grid.rows - 1) else (grid.ymax - (row + 1) * grid.dy)
        xmax = grid.xmax if col == (grid.cols - 1) else (grid.xmin + (col + 1) * grid.dx)
        ymax = grid.ymax - row * grid.dy
        return Box(xmin, ymin, xmax, ymax)

    if col == 0:
        xmin = _DBL_LOWEST
    elif col == grid.cols - 1:
        xmin = grid.xmax
    else:
        xmin = grid.xmin + (col - 1) * grid.dx

    span = grid.cols - col
    if span == 1:
        xmax = _DBL_MAX
    elif span == 2:
        xmax = grid.xmax
    else:
        xmax = grid.xmin + col * grid.dx

    if row == 0:
        ymax = _DBL_MAX
    elif row == grid.rows - 1:
        ymax = grid.ymin
    else:
        ymax = grid.ymax - (row - 1) * grid.dy

    span = grid.rows - row
    if span == 1:
        ymin = _DBL_LOWEST
    elif span == 2:
        ymin = grid.ymin
    else:
        ymin = grid.ymax - row * grid.dy

    return Box(xmin, ymin, xmax, ymax)


def make_infinite(grid: Grid) -> Grid:
    return Grid(grid.extent, grid.dx, grid.dy, padding=1)


def make_finite(grid: Grid) -> Grid:
    return Grid(grid.extent, grid.dx, grid.dy, padding=0)


def parse_grid(spec: dict) -> tuple[Grid, np.ndarray | None]:
    """Read a grid dict. Row 0 of ``values`` is the northern row."""
    try:
        xmin = float(spec["xmin"])
        xmax = float(spec["xmax"])
        ymin = float(spec["ymin"])
        ymax = float(spec["ymax"])
    except KeyError as exc:
        raise ValueError("grid requires xmin, xmax, ymin, and ymax") from exc

    values = spec.get("values", None)
    if values is not None:
        arr = np.asarray(values, dtype=np.float64)
        if arr.ndim != 2:
            raise ValueError("grid values must be a 2-d sequence")
        nrows, ncols = arr.shape
    else:
        if "nrows" not in spec or "ncols" not in spec:
            raise ValueError("grid requires values or nrows and ncols")
        nrows = int(spec["nrows"])
        ncols = int(spec["ncols"])
        arr = None
    if nrows <= 0 or ncols <= 0:
        raise ValueError("grid must have a positive number of rows and columns")
    dx = (xmax - xmin) / ncols
    dy = (ymax - ymin) / nrows
    grid = Grid(Box(xmin, ymin, xmax, ymax), dx, dy, padding=0)
    if grid.rows != nrows or grid.cols != ncols:
        raise ValueError("grid extent and resolution do not match nrows and ncols")
    return grid, arr


def as_features(y) -> list[str]:
    if isinstance(y, str):
        return [y]
    return [str(item) for item in y]


def matrix_to_lists(arr: np.ndarray) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(arr.shape[0]):
        out.append([float(arr[i, j]) for j in range(arr.shape[1])])
    return out


def extent_dict(grid: Grid, values) -> dict:
    return {
        "values": values,
        "xmin": grid.xmin,
        "xmax": grid.xmax,
        "ymin": grid.ymin,
        "ymax": grid.ymax,
    }


def view_raster(src: np.ndarray, src_grid: Grid, dest_grid: Grid) -> np.ndarray:
    """``RasterView``: sample ``src`` onto ``dest_grid``. Outside cells are NaN."""
    out = np.full((dest_grid.rows, dest_grid.cols), np.nan, dtype=np.float64)
    if src_grid.empty() or src_grid.rows == 0 or src_grid.cols == 0 or dest_grid.rows == 0:
        return out
    dis_x = src_grid.dx / dest_grid.dx
    dis_y = src_grid.dy / dest_grid.dy
    if abs(dis_x - cpp_round(dis_x)) > 1e-6 or abs(dis_y - cpp_round(dis_y)) > 1e-6:
        raise RuntimeError("Must construct view at resolution that is an integer multiple of original.")
    if dis_x < 0 or dis_y < 0:
        raise RuntimeError("Must construct view at equal or higher resolution than original.")
    rx = cpp_round(dis_x)
    ry = cpp_round(dis_y)
    x_off = cpp_round((dest_grid.xmin - src_grid.xmin) / dest_grid.dx)
    y_off = cpp_round((src_grid.ymax - dest_grid.ymax) / dest_grid.dy)
    src_rows, src_cols = src.shape
    for row in range(dest_grid.rows):
        for col in range(dest_grid.cols):
            if x_off < 0 and (-x_off) > col:
                continue
            if y_off < 0 and (-y_off) > row:
                continue
            i0 = (row + y_off) // ry
            j0 = (col + x_off) // rx
            if i0 < 0 or j0 < 0 or i0 > src_rows - 1 or j0 > src_cols - 1:
                continue
            out[row, col] = src[i0, j0]
    return out
