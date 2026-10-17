"""Extract cell values and coverage, or a named summary.

Statistics follow ``raster_stats.h`` and ``CPP_stats`` in ``src/exact_extract.cpp``.
Coverage fractions are ``float``; ``mean`` divides the two ``float`` reductions.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from ._grid import Grid, as_features, parse_grid, view_raster
from ._geos import geos
from ._intersect import cartesian_cell_area, raster_cell_intersection

_STORED = {
    "mode",
    "majority",
    "minority",
    "variety",
    "median",
    "quantile",
    "frac",
    "weighted_frac",
}
_WEIGHTED = {
    "weighted_mean",
    "weighted_sum",
    "weighted_stdev",
    "weighted_variance",
    "weighted_frac",
}


class _West:
    def __init__(self) -> None:
        self.sum_w = 0.0
        self.mean = 0.0
        self.t = 0.0

    def process(self, x: float, w: float) -> None:
        if w == 0.0:
            return
        mean_old = self.mean
        self.sum_w += w
        self.mean += (w / self.sum_w) * (x - mean_old)
        self.t += w * (x - mean_old) * (x - self.mean)

    def variance(self) -> float:
        return self.t / self.sum_w

    def stdev(self) -> float:
        return math.sqrt(self.variance())

    def coefficient_of_variation(self) -> float:
        return self.stdev() / self.mean


class _Quantiles:
    def __init__(self) -> None:
        self.elems: list[dict] = []
        self.ready = False
        self.sum_w = 0.0

    def process(self, x: float, w: float) -> None:
        if w < 0.0:
            raise RuntimeError("Weighted quantile calculation does not support negative weights.")
        if not math.isfinite(w):
            raise RuntimeError("Weighted quantile does not support non-finite weights.")
        self.ready = False
        self.elems.append({"x": x, "w": w, "cumsum": 0.0, "s": 0.0})

    def _prepare(self) -> None:
        self.elems.sort(key=lambda item: item["x"])
        self.sum_w = 0.0
        n = len(self.elems)
        for i, elem in enumerate(self.elems):
            self.sum_w += elem["w"]
            if i == 0:
                elem["s"] = 0.0
                elem["cumsum"] = elem["w"]
            else:
                prev = self.elems[i - 1]
                elem["cumsum"] = prev["cumsum"] + elem["w"]
                elem["s"] = i * elem["w"] + (n - 1) * prev["cumsum"]
        self.ready = True

    def quantile(self, q: float) -> float:
        if not math.isfinite(q) or q < 0.0 or q > 1.0:
            raise RuntimeError("Quantile must be between 0 and 1.")
        if not self.ready:
            self._prepare()
        target = self.sum_w * (len(self.elems) - 1) * q
        right = 0
        while right < len(self.elems) and not (target < self.elems[right]["s"]):
            right += 1
        left = self.elems[right - 1]
        if right == len(self.elems):
            return left["x"]
        nxt = self.elems[right]
        return left["x"] + (target - left["s"]) * (nxt["x"] - left["x"]) / (nxt["s"] - left["s"])


class RasterStats:
    def __init__(self, store_values: bool = False) -> None:
        self._min = sys_max()
        self._max = -sys_max()
        self.sum_ciwi = 0.0
        self.sum_ci = 0.0
        self.sum_xici = 0.0
        self.sum_xiciwi = 0.0
        self.store_values = store_values
        self._var = _West()
        self._wvar = _West()
        self.freq: dict[float, list[float]] = {}
        self._quantiles: _Quantiles | None = None

    def process_value(self, val: float, coverage, weight: float) -> None:
        cov = float(np.float32(coverage))
        self.sum_ci += cov
        self.sum_xici += val * cov
        self._var.process(val, cov)
        ciwi = cov * weight
        self.sum_ciwi += ciwi
        self.sum_xiciwi += val * ciwi
        self._wvar.process(val, ciwi)
        if val < self._min:
            self._min = val
        if val > self._max:
            self._max = val
        if self.store_values:
            entry = self.freq.setdefault(float(val), [0.0, 0.0])
            entry[0] += cov
            entry[1] += ciwi
            self._quantiles = None

    def process(self, coverage: np.ndarray, values: np.ndarray, weights: np.ndarray | None = None) -> None:
        for i in range(coverage.shape[0]):
            for j in range(coverage.shape[1]):
                pct = coverage[i, j]
                if not (pct > 0):
                    continue
                val = float(values[i, j])
                if math.isnan(val):
                    continue
                if weights is None:
                    self.process_value(val, pct, 1.0)
                else:
                    weight = float(weights[i, j])
                    if math.isnan(weight):
                        weight = float("nan")
                    self.process_value(val, pct, weight)

    def sum(self) -> float:
        return float(np.float32(self.sum_xici))

    def count(self) -> float:
        return float(np.float32(self.sum_ci))

    def mean(self) -> float:
        return float(np.float32(self.sum_xici) / np.float32(self.sum_ci))

    def weighted_sum(self) -> float:
        return float(np.float32(self.sum_xiciwi))

    def weighted_count(self) -> float:
        return float(np.float32(self.sum_ciwi))

    def weighted_mean(self) -> float:
        return float(np.float32(self.sum_xiciwi) / np.float32(self.sum_ciwi))

    def minimum(self):
        if self.sum_ci == 0.0:
            return None
        return self._min

    def maximum(self):
        if self.sum_ci == 0.0:
            return None
        return self._max

    def variance(self) -> float:
        return float(np.float32(self._var.variance()))

    def stdev(self) -> float:
        return float(np.float32(self._var.stdev()))

    def coefficient_of_variation(self) -> float:
        return float(np.float32(self._var.coefficient_of_variation()))

    def weighted_variance(self) -> float:
        return float(np.float32(self._wvar.variance()))

    def weighted_stdev(self) -> float:
        return float(np.float32(self._wvar.stdev()))

    def variety(self) -> float:
        return float(len(self.freq))

    def mode(self):
        if not self.freq:
            return None
        best_val = None
        best_ci = None
        for val, (ci, _wi) in self.freq.items():
            if best_val is None or ci > best_ci or (ci == best_ci and val > best_val):
                best_val = val
                best_ci = ci
        return best_val

    def minority(self):
        if not self.freq:
            return None
        best_val = None
        best_ci = None
        for val, (ci, _wi) in self.freq.items():
            if best_val is None or ci < best_ci or (ci == best_ci and val < best_val):
                best_val = val
                best_ci = ci
        return best_val

    def quantile(self, q: float):
        if self.sum_ci == 0.0:
            return None
        if self._quantiles is None:
            wq = _Quantiles()
            for val, (ci, _wi) in self.freq.items():
                wq.process(val, ci)
            self._quantiles = wq
        return self._quantiles.quantile(q)


def sys_max() -> float:
    return float(np.finfo(np.float64).max)


def stat_value(stats: RasterStats, name: str):
    if name == "mean":
        return stats.mean()
    if name == "sum":
        return stats.sum()
    if name == "count":
        return stats.count()
    if name == "min":
        return stats.minimum()
    if name == "max":
        return stats.maximum()
    if name == "median":
        return stats.quantile(0.5)
    if name in ("mode", "majority"):
        return stats.mode()
    if name == "minority":
        return stats.minority()
    if name == "variety":
        return stats.variety()
    if name == "weighted_mean":
        return stats.weighted_mean()
    if name == "weighted_sum":
        return stats.weighted_sum()
    if name == "variance":
        return stats.variance()
    if name == "stdev":
        return stats.stdev()
    if name == "coefficient_of_variation":
        return stats.coefficient_of_variation()
    if name == "weighted_variance":
        return stats.weighted_variance()
    if name == "weighted_stdev":
        return stats.weighted_stdev()
    if name == "quantile":
        raise ValueError("Quantiles not specified.")
    raise ValueError("Unknown stat: " + name)


def _apply_default(arr: np.ndarray, default) -> np.ndarray:
    if default is None or (isinstance(default, float) and math.isnan(default)):
        return arr
    out = np.array(arr, dtype=np.float64, copy=True)
    bad = np.isnan(out)
    out[bad] = float(default)
    return out


def _coverage_for(grid: Grid, wkt: str) -> tuple[np.ndarray, Grid]:
    ctx = geos()
    geom = ctx.from_wkt(wkt)
    try:
        if ctx.is_empty(geom):
            raise ValueError("Can't get statistics for empty geometry")
        box = ctx.box(geom)
    finally:
        geom.close()
    if not box.intersects(grid.extent):
        return np.zeros((0, 0), dtype=np.float32), Grid.make_empty()
    return raster_cell_intersection(grid.crop(box), wkt)


def _stat_names(fun) -> list[str]:
    if isinstance(fun, str):
        return [fun]
    return [str(item) for item in fun]


def _feature_value(spec, name: str, index: int, n_features: int):
    if isinstance(spec, (list, tuple)):
        return spec[index][name]
    value = spec[name]
    if isinstance(value, (list, tuple)) and not isinstance(value, str) and len(value) == n_features:
        return value[index]
    return value


def exact_extract(
    x,
    y,
    fun=None,
    weights=None,
    coverage_area: bool = False,
    default_value=None,
    default_weight=None,
    include_area: bool = False,
    include_cell: bool = False,
    include_xy: bool = False,
    include_cols=None,
):
    """Extract values covered by ``y``, or summarize them with a C++ stat name.

    ``fun=None`` returns one dict per feature, with ``value`` and
    ``coverage_fraction`` (and ``weight`` when ``weights`` is set). A single
    named stat returns a list of floats. Several named stats return a list of
    dicts.
    """
    value_grid, values = parse_grid(x)
    if values is None:
        raise ValueError("exact_extract requires grid values")
    weight_grid = None
    weight_values = None
    if weights is not None:
        weight_grid, weight_values = parse_grid(weights)
        if weight_values is None:
            raise ValueError("weights requires grid values")

    features = as_features(y)
    names = _stat_names(fun) if fun is not None else []
    if fun is not None and len(names) == 0:
        raise ValueError("No summary operations provided.")

    if names:
        if include_xy:
            raise ValueError("include_xy must be FALSE for named summary operations")
        if include_cell:
            raise ValueError("include_cell must be FALSE for named summary operations")
        if include_area:
            raise ValueError("include_area must be FALSE for named summary operations")
        if include_cols is not None:
            raise ValueError(
                "include_cols not supported for named_summary operations (see argument append_cols)"
            )
        if any(name in _WEIGHTED or name.startswith("weighted") for name in names) and weights is None:
            raise ValueError("Weighted stat requested but no weights provided.")
        if weights is not None and not any(name.startswith("weighted") for name in names):
            warnings.warn("Weights provided but no requested operations use them.", stacklevel=2)

    if weight_grid is None:
        common = value_grid
    else:
        common = value_grid.common_grid(weight_grid, 1e-3)
        if (common.dx < value_grid.dx or common.dy < value_grid.dy) and any(
            name in ("count", "sum") for name in names
        ):
            raise ValueError(
                "Cannot compute 'count' or 'sum' when value raster is disaggregated to resolution of weights."
            )

    store = any(name in _STORED for name in names)
    results = []
    for feature_index, wkt in enumerate(features):
        cov, cov_grid = _coverage_for(common, wkt)
        if names:
            if coverage_area and cov.size:
                area = cartesian_cell_area(cov_grid)
                cov = np.float32(cov.astype(np.float64) * area)
            stats = RasterStats(store)
            if cov.size and not cov_grid.empty():
                sampled = _apply_default(view_raster(values, value_grid, cov_grid), default_value)
                weight_sampled = None
                if weight_values is not None:
                    weight_sampled = _apply_default(
                        view_raster(weight_values, weight_grid, cov_grid),
                        default_weight,
                    )
                stats.process(cov, sampled, weight_sampled)
            if len(names) == 1:
                results.append(stat_value(stats, names[0]))
            else:
                results.append({name: stat_value(stats, name) for name in names})
            continue

        results.append(
            _cell_table(
                cov,
                cov_grid,
                values,
                value_grid,
                weight_values,
                weight_grid,
                coverage_area,
                default_value,
                default_weight,
                include_area,
                include_cell,
                include_xy,
                include_cols,
                feature_index,
                len(features),
            )
        )
    return results


def _cell_table(
    cov,
    cov_grid,
    values,
    value_grid,
    weight_values,
    weight_grid,
    coverage_area,
    default_value,
    default_weight,
    include_area,
    include_cell,
    include_xy,
    include_cols,
    feature_index,
    n_features,
) -> dict:
    coverage_name = "coverage_area" if coverage_area else "coverage_fraction"
    columns: dict[str, list] = {}
    if include_cols:
        names = list(include_cols) if not isinstance(include_cols, (list, tuple)) else list(include_cols[0])
        for name in names:
            columns[name] = []
    columns["value"] = []
    if weight_values is not None:
        columns["weight"] = []
    if include_xy:
        columns["x"] = []
        columns["y"] = []
    if include_cell:
        columns["cell"] = []
    if include_area:
        columns["area"] = []
    columns[coverage_name] = []

    if cov.size == 0 or cov_grid.empty():
        return columns

    sampled = _apply_default(view_raster(values, value_grid, cov_grid), default_value)
    weight_sampled = None
    if weight_values is not None:
        weight_sampled = _apply_default(
            view_raster(weight_values, weight_grid, cov_grid),
            default_weight,
        )
    coverage = cov.astype(np.float64)
    if coverage_area:
        coverage = coverage * cartesian_cell_area(cov_grid)
    area = cartesian_cell_area(cov_grid) if include_area else None

    for i in range(coverage.shape[0]):
        for j in range(coverage.shape[1]):
            fraction = float(coverage[i, j])
            if not (fraction > 0.0):
                continue
            if include_cols:
                for name in columns:
                    if name in ("value", "weight", "x", "y", "cell", "area", coverage_name):
                        continue
                    columns[name].append(_feature_value(include_cols, name, feature_index, n_features))
            columns["value"].append(float(sampled[i, j]))
            if weight_sampled is not None:
                columns["weight"].append(float(weight_sampled[i, j]))
            if include_xy:
                columns["x"].append(cov_grid.x_for_col(j))
                columns["y"].append(cov_grid.y_for_row(i))
            if include_cell:
                columns["cell"].append(_cell_number(value_grid, cov_grid.x_for_col(j), cov_grid.y_for_row(i)))
            if include_area:
                columns["area"].append(area)
            columns[coverage_name].append(fraction)
    return columns


def _cell_number(grid: Grid, x: float, y: float):
    if x < grid.xmin or x > grid.xmax or y < grid.ymin or y > grid.ymax:
        return None
    if x == grid.xmax:
        col = grid.cols - 1
    else:
        col = int(math.trunc((x - grid.xmin) / grid.dx))
    if y == grid.ymin:
        row = grid.rows - 1
    else:
        row = int(math.trunc((grid.ymax - y) / grid.dy))
    return row * grid.cols + col + 1
