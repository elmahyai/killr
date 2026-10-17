"""st_is_longlat from sf 1.1-3.

Geographic means GDAL's OSRIsGeographic after the crs is read the way
st_crs and crs_parameters read it. A missing crs is None, which is R's NA.
"""

from __future__ import annotations

import ctypes
import math
import sys
import warnings
from ctypes.util import find_library

_NA = object()
_EPS = math.sqrt(sys.float_info.epsilon)
_LIB = None
_HANDLER = None
_QUIET = None


def _na_crs():
    return {"class": ("crs",), "input": None, "wkt": None}


def _classes(x):
    if isinstance(x, dict):
        raw = x.get("class", ())
    else:
        raw = getattr(x, "r_class", None)
        if raw is None:
            return ()
    if raw is None or raw == ():
        return ()
    if isinstance(raw, str):
        return (raw,)
    return tuple(raw)


def _get(x, name):
    if isinstance(x, dict):
        return x.get(name, _NA)
    return getattr(x, name, _NA)


def _is_crs(x):
    return isinstance(x, dict) and "crs" in _classes(x)


def _is_na_crs(x):
    return (
        _is_crs(x)
        and x.get("input") is None
        and x.get("wkt") is None
        and "epsg" not in x
        and "proj4string" not in x
    )


def _gdal():
    global _LIB, _HANDLER, _QUIET
    if _LIB is not None:
        return _LIB
    name = find_library("gdal")
    if not name:
        raise RuntimeError("libgdal is not installed")
    lib = ctypes.CDLL(name)
    handler_type = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)

    def on_error(err_class, err_no, msg):
        text = msg.decode("utf-8", "replace") if msg else ""
        if err_class in (1, 2):
            warnings.warn(f"GDAL Message {err_no}: {text}", UserWarning, stacklevel=1)
        elif err_class in (3, 4):
            warnings.warn(f"GDAL Error {err_no}: {text}", UserWarning, stacklevel=1)
        elif err_class != 0:
            warnings.warn(
                f"Received invalid error class {err_class} (errno {err_no}: {text})",
                UserWarning,
                stacklevel=1,
            )

    def on_quiet(err_class, err_no, msg):
        return None

    _HANDLER = handler_type(on_error)
    _QUIET = handler_type(on_quiet)
    lib.CPLSetErrorHandler.argtypes = [handler_type]
    lib.CPLSetErrorHandler.restype = ctypes.c_void_p
    lib.GDALAllRegister.argtypes = []
    lib.OGRRegisterAll.argtypes = []
    lib.OSRNewSpatialReference.argtypes = [ctypes.c_char_p]
    lib.OSRNewSpatialReference.restype = ctypes.c_void_p
    lib.OSRDestroySpatialReference.argtypes = [ctypes.c_void_p]
    lib.OSRSetFromUserInput.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.OSRSetFromUserInput.restype = ctypes.c_int
    lib.OSRImportFromWkt.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    lib.OSRImportFromWkt.restype = ctypes.c_int
    lib.OSRIsGeographic.argtypes = [ctypes.c_void_p]
    lib.OSRIsGeographic.restype = ctypes.c_int
    lib.OSRExportToWkt.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    lib.OSRExportToWkt.restype = ctypes.c_int
    lib.VSIFree.argtypes = [ctypes.c_void_p]
    lib.CPLSetErrorHandler(_HANDLER)
    lib.GDALAllRegister()
    lib.OGRRegisterAll()
    _LIB = lib
    return lib


def _epsg_string(x):
    if isinstance(x, float):
        if not x.is_integer():
            return "EPSG:" + _r_character(x)
        x = int(x)
    return f"EPSG:{int(x)}"


def _r_character(x):
    """as.character for a double that is not a whole number, close to R's default."""
    text = format(x, ".15g")
    return text


def _user_srs(text):
    """SetFromUserInput. Returns (geographic, wkt) or (None, None) after a GDAL warning."""
    lib = _gdal()
    srs = lib.OSRNewSpatialReference(None)
    if not srs:
        raise RuntimeError("OGR error")
    try:
        err = lib.OSRSetFromUserInput(srs, text.encode("utf-8"))
        if err != 0:
            return None, None
        out = ctypes.c_char_p()
        export_err = lib.OSRExportToWkt(srs, ctypes.byref(out))
        wkt = out.value.decode("utf-8") if out.value else ""
        if out.value:
            lib.VSIFree(out)
        if export_err != 0:
            raise RuntimeError("OGR error")
        return bool(lib.OSRIsGeographic(srs)), wkt
    finally:
        lib.OSRDestroySpatialReference(srs)


def _geographic_wkt(wkt):
    """Import WKT with the silent handler crs_parameters uses, then IsGeographic."""
    lib = _gdal()
    if wkt is None:
        raise RuntimeError("crs not found")
    srs = lib.OSRNewSpatialReference(None)
    if not srs:
        raise RuntimeError("OGR error")
    lib.CPLSetErrorHandler(_QUIET)
    try:
        buf = ctypes.c_char_p(wkt.encode("utf-8"))
        err = lib.OSRImportFromWkt(srs, ctypes.byref(buf))
        if err != 0:
            raise RuntimeError("OGR error")
        return bool(lib.OSRIsGeographic(srs))
    finally:
        lib.CPLSetErrorHandler(_HANDLER)
        lib.OSRDestroySpatialReference(srs)


def _st_crs_numeric(x):
    if isinstance(x, float) and not math.isfinite(x):
        return _na_crs()
    if not isinstance(x, float) and not math.isfinite(float(x)):
        return _na_crs()
    text = _epsg_string(x)
    geographic, wkt = _user_srs(text)
    if geographic is None:
        return _na_crs()
    return {"class": ("crs",), "input": text, "wkt": wkt}


def _st_crs_character(x):
    if x is None:
        return _na_crs()
    geographic, wkt = _user_srs(x)
    if geographic is None:
        raise ValueError(f"invalid crs: {x}")
    return {"class": ("crs",), "input": x, "wkt": wkt}


def _names(x):
    if isinstance(x, dict):
        return [key for key in x.keys() if key != "class"]
    return []


def _fix_crs(x):
    names = _names(x)
    if "epsg" in names and "proj4string" in names:
        # fix_crs signals this with message(), which is not a warning.
        print(
            "old-style crs object detected; please recreate object with a recent sf::st_crs()",
            file=sys.stderr,
        )
        epsg = _get(x, "epsg")
        if epsg is not _NA and epsg is not None and not (isinstance(epsg, float) and math.isnan(epsg)):
            return _st_crs_numeric(epsg)
        proj4 = _get(x, "proj4string")
        if proj4 is _NA or proj4 is None:
            return _na_crs()
        return _st_crs_character(proj4)
    return x


def _geometry(x):
    name = _get(x, "sf_column")
    column = _get(x, name) if name is not _NA else _NA
    if name is _NA or column is _NA or "sfc" not in _classes(column):
        raise RuntimeError(
            'attr(obj, "sf_column") does not point to a geometry column.\n'
            'Did you rename it, without setting st_geometry(obj) <- "newname"?'
        )
    return column


def _st_crs(x):
    if x is None or isinstance(x, bool):
        return _na_crs()
    if isinstance(x, (int, float)):
        return _st_crs_numeric(x)
    if isinstance(x, str):
        return _st_crs_character(x)
    classes = _classes(x)
    if "crs" in classes:
        return x
    if "sf" in classes:
        return _st_crs(_geometry(x))
    if "sfc" in classes:
        return _fix_crs(_get(x, "crs"))
    if "bbox" in classes:
        crs = _get(x, "crs")
        if crs is _NA or crs is None:
            return _na_crs()
        return crs
    return _na_crs()


def _missing_number(value):
    if value is None or value is _NA:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _bbox_values(bb):
    if not isinstance(bb, dict):
        return None
    values = []
    for name in ("xmin", "ymin", "xmax", "ymax"):
        if name not in bb:
            return None
        values.append(bb[name])
    return values


def _out_of_range(bb):
    values = _bbox_values(bb)
    if values is None:
        return False
    if any(_missing_number(value) for value in values):
        return False
    xmin, ymin, xmax, ymax = values
    return (
        xmin < (-180 - _EPS)
        or xmax > (360 + _EPS)
        or ymin < (-90 - _EPS)
        or ymax > (90 + _EPS)
    )


def _st_bbox(x):
    classes = _classes(x)
    if "sf" in classes:
        return _st_bbox(_geometry(x))
    if "sfc" in classes or "bbox" in classes:
        bb = _get(x, "bbox") if "sfc" in classes else x
        return None if bb is _NA else bb
    label = ", ".join(f'"{name}"' for name in classes) if classes else '""'
    raise RuntimeError(
        f"no applicable method for 'st_bbox' applied to an object of class {label}"
    )


def _modern_wkt(crs):
    """crs_parameters repairs an old-style epsg/proj4string list before reading wkt."""
    names = _names(crs)
    if len(names) != 2:
        if not names:
            raise RuntimeError("invalid crs object: no names")
        raise RuntimeError("invalid crs object: wrong length")
    if names[0] == "epsg":
        proj4 = crs.get(names[1])
        if proj4 is None or (isinstance(proj4, float) and math.isnan(proj4)):
            raise RuntimeError("crs not found")
        geographic, wkt = _user_srs(str(proj4))
        if geographic is None:
            raise RuntimeError("crs not found")
        return wkt
    return crs.get("wkt")


def st_is_longlat(x):
    """Whether x has geographic coordinates.

    Returns True for longlat degrees, False for projected coordinates, and
    None when the coordinate reference system is missing. An sfc or stars
    object whose own bbox attribute falls outside [-180, 360] by [-90, 90],
    past sqrt(.Machine$double.eps), warns and still returns True.
    """
    crs = _st_crs(x)
    if crs is _NA or crs is None or _is_na_crs(crs):
        return None
    if not _is_crs(crs):
        raise ValueError('inherits(x, "crs") is not TRUE')
    geographic = _geographic_wkt(_modern_wkt(crs))
    classes = _classes(x)
    bbox = _get(x, "bbox")
    if (
        geographic
        and any(name in classes for name in ("sf", "sfc", "stars"))
        and bbox is not _NA
        and bbox is not None
    ):
        if _out_of_range(_st_bbox(x)):
            warnings.warn(
                "bounding box has potentially an invalid value range for longlat data",
                UserWarning,
                stacklevel=2,
            )
    return geographic
