"""st_bbox from sf 1.1-3.

The bounding box is xmin, ymin, xmax, ymax. An sfc returns the box stored on
it, with the crs of that sfc. A geometry computes the box. The coordinate walk
follows CPL_get_bbox: std::min and std::max, which keep the first value when
the comparison is false, including NA and NaN. Rcpp itself is not used.

Objects are dicts with an R ``class`` tuple.

- POINT: ``xy`` is a coordinate vector. Only the first two positions are used.
- LINESTRING, MULTIPOINT, CIRCULARSTRING: ``xy`` is a matrix, one point per row.
- POLYGON, MULTILINESTRING, TRIANGLE: ``xy`` is a list of those matrices.
- MULTIPOLYGON, POLYHEDRALSURFACE, TIN: ``xy`` is a list of those lists.
- GEOMETRYCOLLECTION and the other curve collections: ``xy`` is a list of
  geometry dicts.
- sfc: ``bbox`` is the stored box and ``crs`` is a crs dict, or None.
- sf: ``sf_column`` names the sfc entry.
- numeric: ``values`` and ``names``. The result is indexed by xmin, ymin,
  xmax, ymax. ``crs`` is keyword-only, matching the argument after ``...``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from sf.st_is_longlat import _gdal, _na_crs, _st_crs

_OMIT = object()
_MISSING = object()
_USE_S2 = True
_FULL = None
_GEOM = None
_WKB_CIRCULARSTRING = 8

_STRUCTURE_NULL = (
    "Calling 'structure(NULL, *)' is deprecated, as NULL cannot have attributes.\n"
    "  Consider 'structure(list(), *)' instead."
)

_POLYGON_FULL = ((0.0, -90.0), (0.0, -90.0))


def _explicit_class(obj):
    if isinstance(obj, dict) and "class" in obj:
        raw = obj["class"]
        if isinstance(raw, str):
            return (raw,)
        return tuple(raw)
    raw = getattr(obj, "r_class", None)
    if raw:
        if isinstance(raw, str):
            return (raw,)
        return tuple(raw)
    return None


def _implicit_chain(obj):
    """Class vector UseMethod walks once the methods package is loaded."""
    if obj is None:
        return ("NULL",)
    if isinstance(obj, bool):
        return ("logical",)
    if isinstance(obj, str):
        return ("character",)
    if isinstance(obj, complex):
        return ("complex",)
    if isinstance(obj, int):
        return ("integer", "numeric")
    if isinstance(obj, float):
        return ("double", "numeric")
    if isinstance(obj, np.ndarray):
        chain = []
        if obj.ndim == 2:
            chain.extend(("matrix", "array"))
        elif obj.ndim > 1:
            chain.append("array")
        if np.issubdtype(obj.dtype, np.bool_):
            chain.append("logical")
        elif np.issubdtype(obj.dtype, np.integer):
            chain.extend(("integer", "numeric"))
        elif np.issubdtype(obj.dtype, np.floating):
            chain.extend(("double", "numeric"))
        elif np.issubdtype(obj.dtype, np.complexfloating):
            chain.append("complex")
        else:
            chain.append("character")
        return tuple(chain)
    return ("list",)


def _dispatch_classes(obj):
    explicit = _explicit_class(obj)
    if explicit is not None:
        return explicit
    return _implicit_chain(obj)


def _no_method(classes):
    if len(classes) == 1:
        shown = f'"{classes[0]}"'
    else:
        inner = ", ".join(f"'{name}'" for name in classes)
        shown = f'"c({inner})"'
    return f"no applicable method for 'st_bbox' applied to an object of class {shown}"


def _as_coord(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, np.integer)):
        return float(value)
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return float("nan")
        return float(value)
    return value


def _is_na(value):
    """R ISNA. A plain NaN is not NA."""
    return value is None


def _is_missing(value):
    """R is.na: NA and NaN."""
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return True
    return False


def _lt(left, right):
    if left is None or right is None:
        return False
    if isinstance(left, (float, np.floating)) and math.isnan(float(left)):
        return False
    if isinstance(right, (float, np.floating)) and math.isnan(float(right)):
        return False
    return left < right


def _cpp_min(left, right):
    """std::min(left, right). The first value wins when ``<`` is false."""
    if _lt(right, left):
        return right
    return left


def _cpp_max(left, right):
    """std::max(left, right)."""
    if _lt(left, right):
        return right
    return left


def _bb_wrap(values, crs=_OMIT):
    if len(values) != 4:
        raise RuntimeError("length(bb) == 4 is not TRUE")
    out = {
        "class": ("bbox",),
        "xmin": _as_coord(values[0]),
        "ymin": _as_coord(values[1]),
        "xmax": _as_coord(values[2]),
        "ymax": _as_coord(values[3]),
    }
    if crs is not _OMIT:
        out["crs"] = crs
    return out


def _na_bbox():
    return _bb_wrap((None, None, None, None), crs=_na_crs())


def _full_bbox():
    global _FULL
    if _FULL is None:
        _FULL = _bb_wrap((-180.0, -90.0, 180.0, 90.0), crs=_st_crs("OGC:CRS84"))
    return {
        "class": ("bbox",),
        "xmin": _FULL["xmin"],
        "ymin": _FULL["ymin"],
        "xmax": _FULL["xmax"],
        "ymax": _FULL["ymax"],
        "crs": _FULL["crs"],
    }


def _matrix_rows(mat):
    if isinstance(mat, np.ndarray):
        if mat.ndim != 2:
            raise RuntimeError("index out of bounds")
        if mat.shape[0] == 0:
            return []
        return [list(row) for row in mat.tolist()]
    if isinstance(mat, (list, tuple)):
        if len(mat) == 0:
            return []
        first = mat[0]
        if isinstance(first, (list, tuple, np.ndarray)):
            return [list(row) for row in mat]
        return [list(mat)]
    raise RuntimeError("index out of bounds")


def _matrix_length(mat):
    rows = _matrix_rows(mat)
    if not rows:
        return 0
    return len(rows) * len(rows[0])


def _numpy_ok_value(value):
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, np.integer)):
        return True
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return False
        if number == 0.0 and math.copysign(1.0, number) < 0.0:
            return False
        return True
    return False


def _numpy_ok(rows):
    for row in rows:
        if len(row) < 2:
            return False
        if not _numpy_ok_value(row[0]) or not _numpy_ok_value(row[1]):
            return False
    return True


def _cpl_depth1(matrices):
    """CPL_get_bbox at depth 1: a list of coordinate matrices."""
    blocks = []
    sequential = False
    for mat in matrices:
        rows = _matrix_rows(mat)
        if not rows:
            continue
        if not _numpy_ok(rows):
            sequential = True
        blocks.append(rows)
    if not blocks:
        return [None, None, None, None]
    if not sequential:
        flat = [row for rows in blocks for row in rows]
        xs = np.fromiter((row[0] for row in flat), dtype=np.float64, count=len(flat))
        ys = np.fromiter((row[1] for row in flat), dtype=np.float64, count=len(flat))
        return [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
    bb = [None, None, None, None]
    initialised = False
    for rows in blocks:
        if not initialised:
            if len(rows[0]) < 2:
                raise RuntimeError("index out of bounds")
            bb[0] = bb[2] = _as_coord(rows[0][0])
            bb[1] = bb[3] = _as_coord(rows[0][1])
            initialised = True
        for row in rows:
            if len(row) < 2:
                raise RuntimeError("index out of bounds")
            x = _as_coord(row[0])
            y = _as_coord(row[1])
            bb[0] = _cpp_min(x, bb[0])
            bb[1] = _cpp_min(y, bb[1])
            bb[2] = _cpp_max(x, bb[2])
            bb[3] = _cpp_max(y, bb[3])
    return bb


def _cpl_recursive(items, depth):
    bb = [None, None, None, None]
    for i, child in enumerate(items):
        if depth - 1 == 1:
            bbi = _cpl_depth1(child)
        else:
            bbi = _cpl_recursive(child, depth - 1)
        if not _is_na(bbi[0]):
            if i == 0:
                bb = list(bbi)
            else:
                bb[0] = _cpp_min(bbi[0], bb[0])
                bb[1] = _cpp_min(bbi[1], bb[1])
                bb[2] = _cpp_max(bbi[2], bb[2])
                bb[3] = _cpp_max(bbi[3], bb[3])
    return bb


def _r_min(values):
    kept = [value for value in values if not _is_missing(value)]
    if not kept:
        warnings.warn("no non-missing arguments to min; returning Inf", UserWarning)
        return math.inf
    out = kept[0]
    for value in kept[1:]:
        if value < out:
            out = value
    return out


def _r_max(values):
    kept = [value for value in values if not _is_missing(value)]
    if not kept:
        warnings.warn("no non-missing arguments to max; returning -Inf", UserWarning)
        return -math.inf
    out = kept[0]
    for value in kept[1:]:
        if out < value:
            out = value
    return out


def _identical_full_ring(rows):
    if len(rows) != 2:
        return False
    for row, target in zip(rows, _POLYGON_FULL):
        if len(row) != 2:
            return False
        for got, exp in zip(row, target):
            if type(got) is int or isinstance(got, np.integer):
                return False
            if got is None or isinstance(got, bool):
                return False
            if not isinstance(got, (float, np.floating)):
                return False
            number = float(got)
            if math.isnan(number):
                return False
            if number != exp or math.copysign(1.0, number) != math.copysign(1.0, exp):
                return False
    return True


def _is_full_polygon(obj):
    if not _USE_S2:
        return False
    classes = _explicit_class(obj) or ()
    if "POLYGON" not in classes:
        return False
    rings = obj["xy"]
    if len(rings) != 1:
        return False
    return _identical_full_ring(_matrix_rows(rings[0]))


def _bbox_point(obj, *args, **kwargs):
    xy = obj["xy"]
    if isinstance(xy, np.ndarray):
        xy = xy.tolist()
    else:
        xy = list(xy)
    x = xy[0] if len(xy) >= 1 else None
    y = xy[1] if len(xy) >= 2 else None
    return _bb_wrap((x, y, x, y))


def _bbox_mtrx(obj, *args, **kwargs):
    if _matrix_length(obj["xy"]) == 0:
        return _na_bbox()
    return _bb_wrap(_cpl_depth1([obj["xy"]]))


def _bbox_mtrx_set(obj, *args, **kwargs):
    if len(obj["xy"]) == 0:
        return _na_bbox()
    return _bb_wrap(_cpl_depth1(obj["xy"]))


def _bbox_mtrx_set_set(obj, *args, **kwargs):
    if len(obj["xy"]) == 0:
        return _na_bbox()
    return _bb_wrap(_cpl_recursive(obj["xy"], 2))


def _bbox_polygon(obj, *args, **kwargs):
    if _is_full_polygon(obj):
        return _full_bbox()
    return _bbox_mtrx_set(obj)


def _bbox_list(obj, *args, **kwargs):
    geoms = obj["xy"]
    if len(geoms) == 0:
        return _na_bbox()
    columns = []
    for geom in geoms:
        bb = st_bbox(geom)
        columns.append((bb["xmin"], bb["ymin"], bb["xmax"], bb["ymax"]))
    if all(_is_missing(column[0]) for column in columns):
        return _na_bbox()
    return _bb_wrap((
        _r_min(column[0] for column in columns),
        _r_min(column[1] for column in columns),
        _r_max(column[2] for column in columns),
        _r_max(column[3] for column in columns),
    ))


def _geom_lib():
    global _GEOM
    lib = _gdal()
    if _GEOM is lib:
        return lib
    lib.OGR_G_CreateGeometry.argtypes = [ctypes_int()]
    lib.OGR_G_CreateGeometry.restype = ctypes_void()
    lib.OGR_G_AddPoint_2D.argtypes = [ctypes_void(), ctypes_double(), ctypes_double()]
    lib.OGR_G_GetLinearGeometry.argtypes = [ctypes_void(), ctypes_double(), ctypes_void()]
    lib.OGR_G_GetLinearGeometry.restype = ctypes_void()
    lib.OGR_G_GetPointCount.argtypes = [ctypes_void()]
    lib.OGR_G_GetPointCount.restype = ctypes_int()
    lib.OGR_G_GetX.argtypes = [ctypes_void(), ctypes_int()]
    lib.OGR_G_GetX.restype = ctypes_double()
    lib.OGR_G_GetY.argtypes = [ctypes_void(), ctypes_int()]
    lib.OGR_G_GetY.restype = ctypes_double()
    lib.OGR_G_DestroyGeometry.argtypes = [ctypes_void()]
    _GEOM = lib
    return lib


def ctypes_int():
    import ctypes
    return ctypes.c_int


def ctypes_double():
    import ctypes
    return ctypes.c_double


def ctypes_void():
    import ctypes
    return ctypes.c_void_p


def _linearize_circular(rows):
    lib = _geom_lib()
    geom = lib.OGR_G_CreateGeometry(_WKB_CIRCULARSTRING)
    if not geom:
        raise RuntimeError("OGR error")
    line = None
    try:
        for row in rows:
            lib.OGR_G_AddPoint_2D(geom, float(row[0]), float(row[1]))
        line = lib.OGR_G_GetLinearGeometry(geom, 0.0, None)
        if not line:
            print("OGR: Corrupt data", flush=True)
            raise RuntimeError("OGR error")
        count = lib.OGR_G_GetPointCount(line)
        return [[lib.OGR_G_GetX(line, i), lib.OGR_G_GetY(line, i)] for i in range(count)]
    finally:
        if line:
            lib.OGR_G_DestroyGeometry(line)
        lib.OGR_G_DestroyGeometry(geom)


def _bbox_circular(obj, *args, **kwargs):
    rows = _matrix_rows(obj["xy"])
    if not rows:
        return _na_bbox()
    linear = _linearize_circular(rows)
    return st_bbox({"class": ("XY", "LINESTRING", "sfg"), "xy": linear})


def _sfc_crs(obj):
    if not isinstance(obj, dict) or obj.get("crs") is None:
        return None
    return _st_crs(obj)


def _bbox_sfc(obj, *args, **kwargs):
    bb = obj.get("bbox") if isinstance(obj, dict) else None
    crs = _sfc_crs(obj)
    if bb is None:
        warnings.warn(_STRUCTURE_NULL, UserWarning)
        out = {"class": ("list",)}
        if crs is not None:
            out["crs"] = crs
        return out
    out = {
        "class": ("bbox",),
        "xmin": _as_coord(bb["xmin"]),
        "ymin": _as_coord(bb["ymin"]),
        "xmax": _as_coord(bb["xmax"]),
        "ymax": _as_coord(bb["ymax"]),
    }
    if crs is not None:
        out["crs"] = crs
    return out


def _bbox_sf(obj, *args, **kwargs):
    if not isinstance(obj, dict) or "sf_column" not in obj or obj["sf_column"] is None:
        raise RuntimeError("attempt to select less than one element in get1index")
    name = obj["sf_column"]
    ret = obj[name] if name in obj else None
    classes = _explicit_class(ret) if ret is not None else ("NULL",)
    if "sfc" not in classes:
        raise RuntimeError(
            'attr(obj, "sf_column") does not point to a geometry column.\n'
            'Did you rename it, without setting st_geometry(obj) <- "newname"?'
        )
    return st_bbox(ret)


def _stop_pkg(package):
    raise RuntimeError(f"package {package} required, please install it first")


def _bbox_spatial(obj, *args, **kwargs):
    _stop_pkg("sp")


def _bbox_raster(obj, *args, **kwargs):
    _stop_pkg("sp")


def _bbox_extent(obj, *args, **kwargs):
    _stop_pkg("raster")


def _bbox_spat(obj, *args, **kwargs):
    _stop_pkg("terra")


def _numeric_parts(obj):
    if isinstance(obj, dict):
        return list(obj.get("values", [])), obj.get("names")
    if isinstance(obj, (bool, int, float)):
        return [obj], None
    if isinstance(obj, np.ndarray):
        return obj.reshape(-1, order="F").tolist(), None
    return list(obj), None


def _bbox_numeric(obj, *args, **kwargs):
    crs = kwargs.get("crs", _MISSING)
    values, names = _numeric_parts(obj)
    picked = []
    for name in ("xmin", "ymin", "xmax", "ymax"):
        if not names:
            picked.append(None)
            continue
        found = None
        hit = False
        for value, label in zip(values, names):
            if label == name:
                found = value
                hit = True
                break
        picked.append(found if hit else None)
    crs_obj = _na_crs() if crs is _MISSING else _st_crs(crs)
    return _bb_wrap(picked, crs=crs_obj)


def _bbox_bbox(obj, *args, **kwargs):
    return obj


_METHODS = {
    "POINT": _bbox_point,
    "MULTIPOINT": _bbox_mtrx,
    "LINESTRING": _bbox_mtrx,
    "POLYGON": _bbox_polygon,
    "MULTILINESTRING": _bbox_mtrx_set,
    "MULTIPOLYGON": _bbox_mtrx_set_set,
    "GEOMETRYCOLLECTION": _bbox_list,
    "MULTISURFACE": _bbox_list,
    "MULTICURVE": _bbox_list,
    "CURVEPOLYGON": _bbox_list,
    "COMPOUNDCURVE": _bbox_list,
    "POLYHEDRALSURFACE": _bbox_mtrx_set_set,
    "TIN": _bbox_mtrx_set_set,
    "TRIANGLE": _bbox_mtrx_set,
    "CIRCULARSTRING": _bbox_circular,
    "sfc": _bbox_sfc,
    "sf": _bbox_sf,
    "Spatial": _bbox_spatial,
    "Raster": _bbox_raster,
    "Extent": _bbox_extent,
    "SpatExtent": _bbox_spat,
    "SpatRaster": _bbox_spat,
    "SpatVector": _bbox_spat,
    "numeric": _bbox_numeric,
    "bbox": _bbox_bbox,
}


def st_bbox(obj, *args, **kwargs):
    """Bounding box of a geometry, feature, or named numeric vector.

    Returns a dict with class ``bbox`` and xmin, ymin, xmax, ymax. A missing
    coordinate is None, which is R's NA. ``crs`` is present when R stores that
    attribute. An sfc whose bbox attribute is missing warns and returns an
    empty list, which is what ``structure(NULL, crs = ...)`` does in R 4.5.
    """
    classes = _dispatch_classes(obj)
    for name in classes:
        method = _METHODS.get(name)
        if method is not None:
            return method(obj, *args, **kwargs)
    raise RuntimeError(_no_method(classes))
