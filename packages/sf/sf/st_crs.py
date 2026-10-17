"""st_crs from sf 1.1-3.

A crs is a dict with class ``crs``, ``input``, and ``wkt``. Missing values are
None, which is R's NA. ``wkt`` is GDAL WKT2 with MULTILINE=YES, after the
traditional GIS axis order sf uses by default. Rcpp is not used; the same
GDAL calls are made with ctypes.

``parameters=True`` is honored only for sfc, sf, and crs, as in R. The
measured fields come from GDAL. ``ud_unit`` is None: the R value is a units
object, and that package is not part of this translation. Semi-major and
semi-minor stay bare numbers for the same reason.

Objects follow the shapes used by st_bbox. An sfc stores ``crs``. An sf
object stores ``sf_column``. A bbox stores ``crs`` when R would. A numpy
array is an atomic vector, and a 2-d array is a matrix.
"""

from __future__ import annotations

import ctypes
import importlib
import math
import sys
import warnings

import numpy as np

# sf/__init__.py binds the name st_is_longlat to the function, which hides the module.
longlat = importlib.import_module("sf.st_is_longlat")

_OAMS_TRADITIONAL = 0
_OGRERR_FAILURE = 6
_BOUND = False
_PROJ = None
_GDALV = None

_GEOM_ERROR = (
    'attr(obj, "sf_column") does not point to a geometry column.\n'
    'Did you rename it, without setting st_geometry(obj) <- "newname"?'
)
_OLD_CRS = (
    "old-style crs object detected; please recreate object with a recent sf::st_crs()"
)


def _lib():
    lib = longlat._gdal()
    global _BOUND
    if _BOUND:
        return lib
    lib.OSRSetAxisMappingStrategy.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.OSRExportToWktEx.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_char_p),
    ]
    lib.OSRExportToWktEx.restype = ctypes.c_int
    lib.OSRExportToPrettyWkt.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.c_int,
    ]
    lib.OSRExportToPrettyWkt.restype = ctypes.c_int
    lib.OSRExportToProj4.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    lib.OSRExportToProj4.restype = ctypes.c_int
    lib.OSRExportToPROJJSON.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.c_void_p,
    ]
    lib.OSRExportToPROJJSON.restype = ctypes.c_int
    lib.OSRGetName.argtypes = [ctypes.c_void_p]
    lib.OSRGetName.restype = ctypes.c_char_p
    lib.OSRGetSemiMajor.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    lib.OSRGetSemiMajor.restype = ctypes.c_double
    lib.OSRGetSemiMinor.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    lib.OSRGetSemiMinor.restype = ctypes.c_double
    lib.OSRGetInvFlattening.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    lib.OSRGetInvFlattening.restype = ctypes.c_double
    lib.OSRIsVertical.argtypes = [ctypes.c_void_p]
    lib.OSRIsVertical.restype = ctypes.c_int
    lib.OSRIsGeocentric.argtypes = [ctypes.c_void_p]
    lib.OSRIsGeocentric.restype = ctypes.c_int
    lib.OSRGetAngularUnits.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    lib.OSRGetAngularUnits.restype = ctypes.c_double
    lib.OSRGetLinearUnits.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
    lib.OSRGetLinearUnits.restype = ctypes.c_double
    lib.OSREPSGTreatsAsLatLong.argtypes = [ctypes.c_void_p]
    lib.OSREPSGTreatsAsLatLong.restype = ctypes.c_int
    lib.OSREPSGTreatsAsNorthingEasting.argtypes = [ctypes.c_void_p]
    lib.OSREPSGTreatsAsNorthingEasting.restype = ctypes.c_int
    lib.OSRGetAuthorityName.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.OSRGetAuthorityName.restype = ctypes.c_char_p
    lib.OSRGetAuthorityCode.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.OSRGetAuthorityCode.restype = ctypes.c_char_p
    lib.OSRGetAxesCount.argtypes = [ctypes.c_void_p]
    lib.OSRGetAxesCount.restype = ctypes.c_int
    lib.OSRGetAxis.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.OSRGetAxis.restype = ctypes.c_char_p
    lib.OSRCopyGeogCSFrom.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.OSRCopyGeogCSFrom.restype = ctypes.c_int
    lib.GDALVersionInfo.argtypes = [ctypes.c_char_p]
    lib.GDALVersionInfo.restype = ctypes.c_char_p
    lib.OSRGetPROJVersion.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.OSRGetPROJVersion.restype = None
    _BOUND = True
    return lib


def _versions():
    global _PROJ, _GDALV
    if _PROJ is None:
        lib = _lib()
        major, minor, patch = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        lib.OSRGetPROJVersion(ctypes.byref(major), ctypes.byref(minor), ctypes.byref(patch))
        _PROJ = f"{major.value}.{minor.value}.{patch.value}"
        _GDALV = lib.GDALVersionInfo(b"RELEASE_NAME").decode("utf-8")
    return _PROJ, _GDALV


def _na_crs():
    return longlat._na_crs()


def _classes_of(obj):
    if isinstance(obj, dict) and "class" in obj:
        raw = obj["class"]
        if isinstance(raw, str):
            return (raw,)
        return tuple(raw)
    return _implicit_class(obj)


def _storage(dtype):
    if dtype.kind == "b":
        return ("logical",)
    if dtype.kind in ("i", "u"):
        return ("integer", "numeric")
    if dtype.kind == "f":
        return ("double", "numeric")
    if dtype.kind == "c":
        return ("complex",)
    if dtype.kind in ("U", "S"):
        return ("character",)
    return ("list",)


def _implicit_class(obj):
    if isinstance(obj, np.ndarray) and obj.ndim == 0:
        return _implicit_class(obj.item())
    if obj is None:
        return ("NULL",)
    if isinstance(obj, (bool, np.bool_)):
        return ("logical",)
    if isinstance(obj, str):
        return ("character",)
    if isinstance(obj, (int, np.integer)) and not isinstance(obj, bool):
        return ("integer", "numeric")
    if isinstance(obj, (float, np.floating)):
        return ("double", "numeric")
    if isinstance(obj, complex):
        return ("complex",)
    if isinstance(obj, np.ndarray):
        chain = []
        if obj.ndim == 2:
            chain.extend(("matrix", "array"))
        elif obj.ndim > 2:
            chain.append("array")
        chain.extend(_storage(obj.dtype))
        return tuple(chain)
    return ("list",)


def _r_names(obj):
    if not isinstance(obj, dict):
        return []
    return [key for key in obj.keys() if key != "class"]


def _is_crs(obj):
    return isinstance(obj, dict) and "crs" in _classes_of(obj)


def _is_na_crs(obj):
    return (
        _is_crs(obj)
        and obj.get("input") is None
        and obj.get("wkt") is None
        and "epsg" not in obj
        and "proj4string" not in obj
    )


def _missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating) and bool(np.isnan(value)):
        return True
    return False


def _size(obj):
    if isinstance(obj, np.ndarray):
        return int(obj.size)
    return 1


def _scalar(obj):
    if isinstance(obj, np.ndarray):
        value = obj.reshape(-1, order="F")[0]
        return value.item() if hasattr(value, "item") else value
    return obj


def _require_length_one(obj):
    """R's if() on is.finite(x) or is.na(x)."""
    n = _size(obj)
    if n == 0:
        raise RuntimeError("argument is of length zero")
    if n > 1:
        raise RuntimeError("the condition has length > 1")


def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _r_character_double(value):
    """R as.character for a double: 15 digits, scientific when it is shorter."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def _as_character_number(value):
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return str(int(value))
    return _r_character_double(float(value))


def _compare_version(left, right):
    """R's compareVersion. Returns -1, 0, or 1."""

    def parts(text):
        chunks = []
        buf = ""
        for ch in text:
            if ch in ".-":
                chunks.append(int(buf) if buf else 0)
                buf = ""
            else:
                buf += ch
        chunks.append(int(buf) if buf else 0)
        return chunks

    a = parts(left)
    b = parts(right)
    n = max(len(a), len(b))
    a.extend([0] * (n - len(a)))
    b.extend([0] * (n - len(b)))
    for x, y in zip(a, b):
        if x != y:
            return -1 if x < y else 1
    return 0


def _rewrite_init(text):
    """make_crs rewrites +init=epsg: only on PROJ 6.0.0 through 6.3.0.

    R's grepl('+init=epsg:') treats the leading plus as a quantifier, so the
    match is the substring init=epsg:.
    """
    proj, _gdal_version = _versions()
    if "init=epsg:" not in text:
        return text
    if _compare_version(proj, "6.0.0") < 0 or _compare_version(proj, "6.3.1") >= 0:
        return text
    parts = text.split(" ")
    if len(parts) > 1:
        warnings.warn(
            "the following proj4string elements are ignored: "
            + " ".join(parts[1:])
            + " ; remove the +init=epsg:XXXX to undo this",
            UserWarning,
            stacklevel=2,
        )
    code = parts[0][11:20]
    number = 0
    saw = False
    for ch in code:
        if not ch.isdigit():
            break
        number = number * 10 + int(ch)
        saw = True
    if not saw:
        number = None
    return "EPSG:NA" if number is None else f"EPSG:{number}"


def _take_export(srs, call, na_on_fail):
    out = ctypes.c_char_p()
    err = call(out)
    text = out.value.decode("utf-8") if out.value else ""
    if out.value:
        _lib().VSIFree(out)
    if err != 0:
        return None if na_on_fail else ""
    return text


def _wkt2(srs):
    lib = _lib()
    opts = (ctypes.c_char_p * 3)(b"MULTILINE=YES", b"FORMAT=WKT2", None)

    def call(out):
        return lib.OSRExportToWktEx(srs, ctypes.byref(out), opts)

    text = _take_export(srs, call, True)
    if text is None:
        raise RuntimeError("OGR error: cannot export to WKT")
    return text


def _crs_from_text(text):
    """CPL_crs_from_input. A failed user string is NA_crs_, with GDAL's warning."""
    text = _rewrite_init(text)
    lib = _lib()
    srs = lib.OSRNewSpatialReference(None)
    if not srs:
        raise RuntimeError("OGR error")
    try:
        lib.OSRSetAxisMappingStrategy(srs, _OAMS_TRADITIONAL)
        if lib.OSRSetFromUserInput(srs, text.encode("utf-8")) != 0:
            return _na_crs()
        return {"class": ("crs",), "input": text, "wkt": _wkt2(srs)}
    finally:
        lib.OSRDestroySpatialReference(srs)


def _quiet_call(fn):
    lib = _lib()
    lib.CPLSetErrorHandler(longlat._QUIET)
    try:
        return fn()
    finally:
        lib.CPLSetErrorHandler(longlat._HANDLER)


def _parameters(crs):
    """CPL_crs_parameters. The caller has already checked inherits(crs)."""
    if _is_na_crs(crs):
        return {"class": ("list",)}
    wkt = crs.get("wkt") if isinstance(crs, dict) else None
    if not isinstance(wkt, str):
        raise RuntimeError("crs not found")

    def read():
        lib = _lib()
        srs = lib.OSRNewSpatialReference(None)
        if not srs:
            raise RuntimeError("OGR error")
        base = None
        try:
            lib.OSRSetAxisMappingStrategy(srs, _OAMS_TRADITIONAL)
            buf = ctypes.c_char_p(wkt.encode("utf-8"))
            if lib.OSRImportFromWkt(srs, ctypes.byref(buf)) != 0:
                raise RuntimeError("OGR error")
            semi_major = lib.OSRGetSemiMajor(srs, None)
            semi_minor = lib.OSRGetSemiMinor(srs, None)
            inv_err = ctypes.c_int()
            lib.OSRGetInvFlattening(srs, ctypes.byref(inv_err))
            if inv_err.value == _OGRERR_FAILURE:
                inv = None
            else:
                inv = lib.OSRGetInvFlattening(srs, None)
            geographic = bool(lib.OSRIsGeographic(srs))
            unit_ptr = ctypes.c_char_p()
            if geographic:
                lib.OSRGetAngularUnits(srs, ctypes.byref(unit_ptr))
            else:
                lib.OSRGetLinearUnits(srs, ctypes.byref(unit_ptr))
            unit = unit_ptr.value.decode("utf-8") if unit_ptr.value else None
            if unit is None or unit == "unknown":
                unit = None
            pretty = _take_export(
                srs,
                lambda out: lib.OSRExportToPrettyWkt(srs, ctypes.byref(out), 0),
                False,
            )
            plain = _take_export(
                srs,
                lambda out: lib.OSRExportToWkt(srs, ctypes.byref(out)),
                False,
            )
            name_ptr = lib.OSRGetName(srs)
            name = name_ptr.decode("utf-8") if name_ptr else ""
            proj4 = _take_export(
                srs,
                lambda out: lib.OSRExportToProj4(srs, ctypes.byref(out)),
                True,
            )
            auth = lib.OSRGetAuthorityName(srs, None)
            code = lib.OSRGetAuthorityCode(srs, None)
            if auth and code and auth == b"EPSG":
                epsg = _atoi(code)
            else:
                epsg = None
            yx = bool(
                lib.OSREPSGTreatsAsLatLong(srs) or lib.OSREPSGTreatsAsNorthingEasting(srs)
            )
            projjson = _take_export(
                srs,
                lambda out: lib.OSRExportToPROJJSON(srs, ctypes.byref(out), None),
                True,
            )
            esri_opts = (ctypes.c_char_p * 3)(b"MULTILINE=YES", b"FORMAT=WKT1_ESRI", None)
            esri = _take_export(
                srs,
                lambda out: lib.OSRExportToWktEx(srs, ctypes.byref(out), esri_opts),
                True,
            )
            if auth and code:
                srid = auth.decode("utf-8") + ":" + code.decode("utf-8")
            else:
                srid = None
            count = lib.OSRGetAxesCount(srs)
            key = b"GEOGCS" if geographic else b"PROJCS"
            axis_names = []
            axis_orient = []
            for i in range(count):
                orient = ctypes.c_int()
                label = lib.OSRGetAxis(srs, key, i, ctypes.byref(orient))
                if label:
                    axis_names.append(label.decode("utf-8"))
                    axis_orient.append(int(orient.value))
                else:
                    axis_names.append(None)
                    axis_orient.append(None)
            base = lib.OSRNewSpatialReference(None)
            if lib.OSRCopyGeogCSFrom(base, srs) == 0:
                gcs = _take_export(
                    base,
                    lambda out: lib.OSRExportToWkt(base, ctypes.byref(out)),
                    True,
                )
            else:
                gcs = None
            geocentric = bool(lib.OSRIsGeocentric(base))
            return {
                "class": ("crs_parameters",),
                "SemiMajor": semi_major,
                "SemiMinor": semi_minor,
                "InvFlattening": inv,
                "IsGeographic": geographic,
                "units_gdal": unit,
                "IsVertical": bool(lib.OSRIsVertical(srs)),
                "WktPretty": pretty,
                "Wkt": plain,
                "Name": name,
                "proj4string": proj4,
                "epsg": epsg,
                "yx": yx,
                "ProjJson": projjson,
                "WKT1_ESRI": esri,
                "srid": srid,
                "axes": {
                    "class": ("data.frame",),
                    "name": axis_names,
                    "orientation": axis_orient,
                },
                "gcs_crs": gcs,
                "is_geocentric": geocentric,
                "ud_unit": None,
            }
        finally:
            if base:
                lib.OSRDestroySpatialReference(base)
            lib.OSRDestroySpatialReference(srs)

    return _quiet_call(read)


def _atoi(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    sign = 1
    i = 0
    if text[:1] == "-":
        sign = -1
        i = 1
    number = 0
    saw = False
    while i < len(text) and text[i].isdigit():
        number = number * 10 + int(text[i])
        i += 1
        saw = True
    return sign * number if saw else 0


def _try_num(text):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            value = float(text)
    except (TypeError, ValueError):
        return text
    if math.isnan(value):
        return text
    return value


def _proj4_value(proj4, name):
    if not isinstance(proj4, str):
        return None
    values = {}
    for piece in proj4.split(" "):
        if piece == "":
            continue
        parts = piece.split("=")
        # substring(..., 2) drops the first character, which is the plus.
        key = parts[0][1:] if parts[0] else ""
        if len(parts) == 1:
            values[key] = True
        else:
            values[key] = _try_num(parts[1])
    return values.get(name)


def crs_get(x, name):
    """`$.crs`. A stored ``input`` or ``wkt`` is returned as it is.

    Any other name is read from the GDAL parameter list. ``ud_unit`` is None.
    An old-style object with ``proj4string`` warns and is read again through
    st_crs.
    """
    if isinstance(name, (int, np.integer)) and not isinstance(name, bool):
        names = _r_names(x)
        index = int(name) - 1
        if index < 0 or index >= len(names):
            return None
        name = names[index]
    if isinstance(x, dict) and "proj4string" in _r_names(x):
        warnings.warn(
            "CRS uses proj4string, which is deprecated.",
            UserWarning,
            stacklevel=2,
        )
        x = st_crs(x.get("proj4string"))
    if name == "ud_unit":
        return None
    if _is_na_crs(x):
        return None
    if isinstance(x, dict) and name in _r_names(x):
        return x.get(name)
    if not _is_crs(x):
        raise RuntimeError('inherits(x, "crs") is not TRUE')
    params = _parameters(x)
    if name in params and name != "class":
        return params[name]
    return _proj4_value(params.get("proj4string"), name)


def _fix_crs(obj):
    names = _r_names(obj)
    if "epsg" in names and "proj4string" in names:
        print(_OLD_CRS, file=sys.stderr)
        epsg = obj.get("epsg")
        if not _missing(epsg):
            return st_crs(epsg)
        return st_crs(obj.get("proj4string"))
    return obj


def _with_parameters(crs):
    if crs is None or not _is_crs(crs):
        raise RuntimeError('inherits(x, "crs") is not TRUE')
    return _parameters(crs)


def _st_crs_numeric(x, parameters=False):
    _require_length_one(x)
    value = _scalar(x)
    if not _finite(value):
        return _na_crs()
    return _crs_from_text("EPSG:" + _as_character_number(value))


def _st_crs_character(x, parameters=False):
    _require_length_one(x)
    text = _scalar(x)
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return _na_crs()
    if not isinstance(text, str):
        text = str(text)
    crs = _crs_from_text(text)
    if _is_na_crs(crs):
        raise RuntimeError(f"invalid crs: {text}")
    if text == crs.get("wkt") and crs_get(crs, "Name") != "unknown":
        crs = dict(crs)
        crs["input"] = crs_get(crs, "Name")
    return crs


def _st_crs_sfc(x, parameters=False):
    if isinstance(x, dict) and "crs" in x:
        raw = x["crs"]
    else:
        raw = None
    fixed = None if raw is None else _fix_crs(raw)
    if parameters is True:
        return _with_parameters(fixed)
    return fixed


def _st_crs_sf(x, parameters=False):
    if not isinstance(x, dict) or x.get("sf_column") is None:
        raise RuntimeError("attempt to select less than one element in get1index")
    name = x["sf_column"]
    column = x.get(name)
    if "sfc" not in _classes_of(column):
        raise RuntimeError(_GEOM_ERROR)
    return st_crs(column, parameters=parameters)


def _st_crs_bbox(x, parameters=False):
    crs = x.get("crs") if isinstance(x, dict) else None
    if crs is None:
        return _na_crs()
    return crs


def _st_crs_crs(x, parameters=False):
    if parameters is True:
        return _with_parameters(_fix_crs(x))
    return x


def _st_crs_sp_crs(x, parameters=False):
    """st_crs.CRS. ``comment`` is R's comment(); ``projargs`` is the slot."""
    comment = x.get("comment") if isinstance(x, dict) else None
    projargs = x.get("projargs") if isinstance(x, dict) else None
    proj, gdal_version = _versions()
    if comment is None or proj < "6.0.0" or gdal_version < "3.0.0":
        return st_crs(projargs)
    ret = dict(st_crs(comment))
    name = crs_get(ret, "Name")
    ret["input"] = projargs if name == "unknown" else name
    return ret


def _st_crs_raster(x, parameters=False):
    raise RuntimeError("there is no package called \u2018raster\u2019")


def _st_crs_spatial(x, parameters=False):
    raise RuntimeError("package sp required, please install it first")


def _st_crs_spat(x, parameters=False):
    raise RuntimeError("package terra required, please install it first")


_METHODS = {
    "sf": _st_crs_sf,
    "numeric": _st_crs_numeric,
    "character": _st_crs_character,
    "sfc": _st_crs_sfc,
    "bbox": _st_crs_bbox,
    "CRS": _st_crs_sp_crs,
    "crs": _st_crs_crs,
    "Raster": _st_crs_raster,
    "Spatial": _st_crs_spatial,
    "SpatRaster": _st_crs_spat,
    "SpatVector": _st_crs_spat,
}


def st_crs(x, *args, parameters=False, **kwargs):
    """Coordinate reference system of a number, string, sf, sfc, bbox, or crs.

    A numeric value is ``EPSG:`` followed by R's as.character of that number.
    A string is handed to GDAL. An unknown number becomes a missing crs. An
    unknown string is an error. ``parameters=True`` returns the GDAL parameter
    list for an sfc, sf, or crs object.
    """
    for name in _classes_of(x):
        method = _METHODS.get(name)
        if method is not None:
            return method(x, parameters=parameters)
    return _na_crs()
