"""st_coordinates from sf 1.1-3.

Coordinates come back as a matrix. Points are one row each. Lines and
multipoints add L1, polygons and multilines add L1 and L2, and multipolygons
add L1, L2, and L3. Those indexes are 1-based.

``round=True`` with a non-zero precision rounds each coordinate the way
``CPL_write_wkb`` does, then reads that matrix. A negative precision casts
through float32. Rcpp is not used.

Objects are dicts with an R ``class`` tuple, the same shape ``st_bbox`` uses.

- POINT: ``xy`` is a coordinate vector.
- LINESTRING and MULTIPOINT: ``xy`` is a matrix, one point per row.
- POLYGON and MULTILINESTRING: ``xy`` is a list of those matrices.
- MULTIPOLYGON: ``xy`` is a list of those lists.
- sfc: ``geoms`` is the list of geometries and ``precision`` is the numeric tag.
- sf: ``sf_column`` names the sfc entry.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

_NA_BITS = np.uint64(0x7FF00000000007A2)
_NULL = object()
_MISSING = object()

_DIMS = ("XY", "XYZ", "XYM", "XYZM")


class Coordinates:
    """Matrix returned by :func:`st_coordinates`.

    ``data`` is column-major in the same order as R. ``colnames`` is ``None``
    when R's dimnames are NULL. An empty collection with no geometries is a
    logical matrix, which is what ``matrix(nrow = 0, ncol = 2)`` returns.
    """

    def __init__(self, data, colnames, logical=False):
        self.data = data
        self.colnames = colnames
        self.logical = logical

    @property
    def nrow(self):
        return int(self.data.shape[0])

    @property
    def ncol(self):
        return int(self.data.shape[1])


def _classes(obj):
    if isinstance(obj, dict) and "class" in obj:
        raw = obj["class"]
        if isinstance(raw, str):
            return (raw,)
        return tuple(raw)
    if obj is None:
        return ("NULL",)
    if isinstance(obj, bool):
        return ("logical",)
    if isinstance(obj, str):
        return ("character",)
    if isinstance(obj, int):
        return ("integer", "numeric")
    if isinstance(obj, float):
        return ("double", "numeric")
    return ("list",)


def _no_method(classes):
    if len(classes) == 1:
        shown = f'"{classes[0]}"'
    else:
        inner = ", ".join(f"'{name}'" for name in classes)
        shown = f'"c({inner})"'
    return f"no applicable method for 'st_coordinates' applied to an object of class {shown}"


def _is_int(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, np.integer)


def _na_float():
    out = np.empty(1, dtype=np.float64)
    out.view(np.uint64)[0] = _NA_BITS
    return float(out[0])


def _as_float(value):
    if value is None:
        return _na_float()
    return float(value)


def _c_round(prod):
    """C ``round``: halfway cases go away from zero, and a NaN payload stays."""
    if math.isnan(prod) or math.isinf(prod):
        return prod
    return math.copysign(math.floor(abs(prod) + 0.5), prod)


def _make_precise(value, precision):
    if precision < 0.0:
        number = _na_float() if value is None else float(value)
        return float(np.float32(number))
    if value is None:
        return _c_round(_na_float() * precision) / precision
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return _c_round(number * precision) / precision
    return _c_round(number * precision) / precision


def _coerce_logical1(value):
    if isinstance(value, np.ndarray):
        value = value.reshape(-1).tolist()
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise RuntimeError(f"'length = {len(value)}' in coercion to 'logical(1)'")
        value = value[0]
    if isinstance(value, str):
        raise RuntimeError("invalid 'x' type in 'x && y'")
    if value is None:
        return _MISSING
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)):
        return int(value) != 0
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return _MISSING
        return float(value) != 0.0
    raise RuntimeError("invalid 'x' type in 'x && y'")


def _precision_nonzero(precision):
    if precision is _NULL or precision is None:
        raise RuntimeError("missing value where TRUE/FALSE needed")
    if isinstance(precision, np.ndarray):
        precision = precision.reshape(-1).tolist()
    if isinstance(precision, (list, tuple)):
        if len(precision) != 1:
            raise RuntimeError(
                f"'length = {len(precision)}' in coercion to 'logical(1)'"
            )
        precision = precision[0]
    if isinstance(precision, (float, np.floating)) and math.isnan(float(precision)):
        raise RuntimeError("missing value where TRUE/FALSE needed")
    return float(precision) != 0.0


def _wants_round(round_value, obj):
    flag = _coerce_logical1(round_value)
    if flag is _MISSING:
        raise RuntimeError("missing value where TRUE/FALSE needed")
    if not flag:
        return None
    precision = obj["precision"] if isinstance(obj, dict) and "precision" in obj else _NULL
    if not _precision_nonzero(precision):
        return None
    if isinstance(precision, (list, tuple, np.ndarray)):
        precision = list(np.reshape(precision, -1))[0]
    return float(precision)


def _precise_rows(xy, precision):
    if isinstance(xy, np.ndarray):
        if xy.ndim == 1:
            return [_make_precise(value, precision) for value in xy.tolist()]
        return [
            [_make_precise(value, precision) for value in row]
            for row in xy.tolist()
        ]
    if isinstance(xy, (list, tuple)) and xy and not isinstance(xy[0], (list, tuple, np.ndarray)):
        return [_make_precise(value, precision) for value in xy]
    rows = []
    for row in xy:
        if isinstance(row, np.ndarray):
            rows.append([_make_precise(value, precision) for value in row.tolist()])
        else:
            rows.append([_make_precise(value, precision) for value in row])
    return rows


def _apply_precision(geom, precision):
    classes = _classes(geom)
    kind = classes[1] if len(classes) > 1 else ""
    xy = geom["xy"]
    if kind == "POINT":
        new_xy = _precise_rows(xy, precision)
    elif kind in ("POLYGON", "MULTILINESTRING", "TRIANGLE"):
        new_xy = [_precise_rows(ring, precision) for ring in xy]
    elif kind in ("MULTIPOLYGON", "POLYHEDRALSURFACE", "TIN"):
        new_xy = [[_precise_rows(ring, precision) for ring in part] for part in xy]
    else:
        new_xy = _precise_rows(xy, precision)
    copied = dict(geom)
    copied["xy"] = new_xy
    return copied


def _matrix_byrow(values, nrow, integer):
    lendat = len(values)
    if lendat == 0:
        ncol = 0
    else:
        ncol = int(math.ceil(lendat / nrow))
    need = nrow * ncol
    if lendat > 1 and need % lendat != 0:
        warnings.warn(
            f"data length [{lendat}] is not a sub-multiple or multiple of the number of rows [{nrow}]",
            UserWarning,
            stacklevel=3,
        )
    if need == 0:
        dtype = np.int32 if integer else np.float64
        return np.zeros((nrow, ncol), dtype=dtype)
    if integer:
        recycled = [int(values[i % lendat]) for i in range(need)]
        return np.array(recycled, dtype=np.int32).reshape(nrow, ncol)
    recycled = [_as_float(values[i % lendat]) for i in range(need)]
    return np.array(recycled, dtype=np.float64).reshape(nrow, ncol)


def _points(geoms, force_double):
    values = []
    integer = not force_double
    for geom in geoms:
        xy = geom["xy"]
        if isinstance(xy, np.ndarray):
            row = xy.reshape(-1).tolist()
        else:
            row = list(xy)
        if integer and any(not _is_int(value) for value in row):
            integer = False
        values.extend(row)
    return _matrix_byrow(values, len(geoms), integer)


def _dim_width(dim):
    if dim in _DIMS:
        return len(dim)
    return 2


def _read_matrix(xy, dim, force_double):
    width = _dim_width(dim)
    if isinstance(xy, np.ndarray):
        if xy.ndim == 1:
            if xy.size == 0:
                dtype = np.float64 if force_double or not np.issubdtype(xy.dtype, np.integer) else np.int32
                return np.zeros((0, width), dtype=dtype)
            xy = xy.reshape(1, -1)
        if xy.ndim != 2:
            raise RuntimeError("index out of bounds")
        if not force_double and np.issubdtype(xy.dtype, np.integer):
            return np.array(xy, dtype=np.int32, copy=True)
        out = np.empty(xy.shape, dtype=np.float64)
        flat = xy.reshape(-1)
        dest = out.reshape(-1)
        for i, value in enumerate(flat.tolist()):
            dest[i] = _as_float(value)
        return out
    if not isinstance(xy, (list, tuple)):
        raise RuntimeError("index out of bounds")
    if len(xy) == 0:
        return np.zeros((0, width), dtype=np.float64)
    first = xy[0]
    if isinstance(first, (list, tuple, np.ndarray)):
        rows = [list(row) for row in xy]
    else:
        rows = [list(xy)]
    if rows and all(len(row) == 0 for row in rows):
        return np.zeros((len(rows), width), dtype=np.float64)
    ncol = len(rows[0])
    integer = not force_double and all(_is_int(value) for row in rows for value in row)
    if integer:
        return np.array([[int(value) for value in row] for row in rows], dtype=np.int32)
    out = np.empty((len(rows), ncol), dtype=np.float64)
    for i, row in enumerate(rows):
        if len(row) != ncol:
            raise RuntimeError("number of columns of matrices must match (see arg 2)")
        for j, value in enumerate(row):
            out[i, j] = _as_float(value)
    return out


def _rbind(mats):
    if not mats:
        return None
    ncol = mats[0].ncol
    for mat in mats[1:]:
        if mat.ncol != ncol:
            raise RuntimeError("number of columns of matrices must match (see arg 2)")
    integer = all(mat.data.dtype == np.int32 for mat in mats)
    blocks = [mat.data for mat in mats]
    if integer:
        data = np.vstack(blocks).astype(np.int32, copy=False)
    else:
        data = np.vstack([block.astype(np.float64, copy=False) for block in blocks])
    colnames = None if mats[0].colnames is None else list(mats[0].colnames)
    return Coordinates(data, colnames)


def _index_vector(counts):
    total = sum(counts)
    idx = np.empty(total, dtype=np.int32)
    pos = 0
    for number, count in enumerate(counts, start=1):
        if count:
            idx[pos:pos + count] = number
            pos += count
    return idx


def _cbind_index(mat, name, counts):
    idx = _index_vector(counts)
    if mat is None:
        data = np.zeros((0, 2), dtype=np.int32)
        return Coordinates(data, ["", name])
    integer = mat.data.dtype == np.int32
    dtype = np.int32 if integer else np.float64
    if mat.nrow == 0:
        data = np.zeros((0, mat.ncol + 1), dtype=dtype)
    else:
        column = idx.astype(dtype, copy=False).reshape(-1, 1)
        base = mat.data if integer else mat.data.astype(np.float64, copy=False)
        data = np.hstack([base, column])
    if mat.colnames is None:
        colnames = [""] * mat.ncol + [name]
    else:
        colnames = list(mat.colnames) + [name]
    return Coordinates(data, colnames)


def _coord_2(matrices):
    mats = [Coordinates(matrix, None) for matrix in matrices]
    return _cbind_index(_rbind(mats), "L1", [mat.nrow for mat in mats])


def _coord_3(groups):
    mats = [_coord_2(group) for group in groups]
    return _cbind_index(_rbind(mats), "L2", [mat.nrow for mat in mats])


def _coord_4(groups):
    mats = [_coord_3(group) for group in groups]
    return _cbind_index(_rbind(mats), "L3", [mat.nrow for mat in mats])


def _name_dims(mat, dims):
    letters = list(dims)
    ncd = len(letters)
    if mat.colnames is None:
        if ncd != mat.ncol:
            raise RuntimeError("length of 'dimnames' [2] not equal to array extent")
        mat.colnames = letters
        return mat
    names = list(mat.colnames)
    if ncd > len(names):
        raise RuntimeError("length of 'dimnames' [2] not equal to array extent")
    for i, letter in enumerate(letters):
        names[i] = letter
    mat.colnames = names
    return mat


def _coordinates_sfc(obj, round=False):
    geoms = list(obj.get("geoms", []))
    if len(geoms) == 0:
        return Coordinates(np.zeros((0, 2), dtype=bool), None, logical=True)
    precision = _wants_round(round, obj)
    force_double = precision is not None
    if force_double:
        geoms = [_apply_precision(geom, precision) for geom in geoms]
    kind = _classes(obj)[0]
    if kind == "sfc_POINT":
        mat = Coordinates(_points(geoms, force_double), None)
    elif kind in ("sfc_MULTIPOINT", "sfc_LINESTRING"):
        mats = [_read_matrix(geom["xy"], _classes(geom)[0], force_double) for geom in geoms]
        mat = _coord_2(mats)
    elif kind in ("sfc_MULTILINESTRING", "sfc_POLYGON"):
        groups = [
            [_read_matrix(ring, _classes(geom)[0], force_double) for ring in geom["xy"]]
            for geom in geoms
        ]
        mat = _coord_3(groups)
    elif kind == "sfc_MULTIPOLYGON":
        groups = [
            [
                [_read_matrix(ring, _classes(geom)[0], force_double) for ring in part]
                for part in geom["xy"]
            ]
            for geom in geoms
        ]
        mat = _coord_4(groups)
    else:
        raise RuntimeError(f"not implemented for objects of class {kind}")
    return _name_dims(mat, _classes(geoms[0])[0])


def _coordinates_sfg(obj, round=False):
    classes = _classes(obj)
    gtype = classes[1] if len(classes) > 1 else "GEOMETRY"
    sfc = {
        "class": (f"sfc_{gtype}", "sfc"),
        "geoms": [obj],
        "precision": 0.0,
    }
    return _coordinates_sfc(sfc, round=round)


def _coordinates_sf(obj, round=False):
    if not isinstance(obj, dict) or obj.get("sf_column") is None:
        raise RuntimeError("attempt to select less than one element in get1index")
    name = obj["sf_column"]
    ret = obj[name] if name in obj else None
    if "sfc" not in _classes(ret):
        raise RuntimeError(
            'attr(obj, "sf_column") does not point to a geometry column.\n'
            'Did you rename it, without setting st_geometry(obj) <- "newname"?'
        )
    return st_coordinates(ret, round=round)


_METHODS = {
    "sf": _coordinates_sf,
    "sfg": _coordinates_sfg,
    "sfc": _coordinates_sfc,
}


def st_coordinates(x, *args, round=False, **kwargs):
    """Coordinates of a geometry, feature, or geometry list.

    Returns a :class:`Coordinates` matrix. A missing coordinate is R's NA,
    stored with the NA payload. ``round`` is the argument after ``...``, so it
    is read by name. A true ``round`` and a non-zero ``precision`` on an sfc
    rounds coordinates before the matrix is built. An sfg is wrapped with
    precision 0, so rounding does not change it.
    """
    for name in _classes(x):
        method = _METHODS.get(name)
        if method is not None:
            return method(x, round=round)
    raise RuntimeError(_no_method(_classes(x)))
