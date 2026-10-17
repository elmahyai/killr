import contextlib
import io
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/sf")

from sf.st_crs import crs_get, st_crs


def esc(s):
    if s is None:
        return "NA"
    return (
        s.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\x1f", "\\x1f")
        .replace("\x1e", "\\x1e")
    )


def fld_num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "NA"
    return format(float(v), ".17g")


def fld_chr(v):
    if v is None:
        return "NA"
    return esc(v)


def fld_log(v):
    if v is None:
        return "NA"
    return "TRUE" if v else "FALSE"


def fld_int(v):
    if v is None:
        return "NA"
    return str(int(v))


def ser_par(p):
    axes = p["axes"]
    axn = "|".join("NA" if n is None else n for n in axes["name"])
    axo = "|".join("NA" if n is None else str(n) for n in axes["orientation"])
    fields = [
        "SemiMajor=" + fld_num(p["SemiMajor"]),
        "SemiMinor=" + fld_num(p["SemiMinor"]),
        "InvFlattening=" + fld_num(p["InvFlattening"]),
        "IsGeographic=" + fld_log(p["IsGeographic"]),
        "units_gdal=" + fld_chr(p["units_gdal"]),
        "IsVertical=" + fld_log(p["IsVertical"]),
        "WktPretty=" + fld_chr(p["WktPretty"]),
        "Wkt=" + fld_chr(p["Wkt"]),
        "Name=" + fld_chr(p["Name"]),
        "proj4string=" + fld_chr(p["proj4string"]),
        "epsg=" + fld_int(p["epsg"]),
        "yx=" + fld_log(p["yx"]),
        "ProjJson=" + fld_chr(p["ProjJson"]),
        "WKT1_ESRI=" + fld_chr(p["WKT1_ESRI"]),
        "srid=" + fld_chr(p["srid"]),
        "axes_name=" + esc(axn),
        "axes_orientation=" + axo,
        "gcs_crs=" + fld_chr(p["gcs_crs"]),
        "is_geocentric=" + fld_log(p["is_geocentric"]),
    ]
    return "PAR\x1f" + "\x1f".join(fields)


def is_na_crs(val):
    classes = val.get("class", ())
    if isinstance(classes, str):
        classes = (classes,)
    return (
        "crs" in classes
        and val.get("input") is None
        and val.get("wkt") is None
        and "epsg" not in val
        and "proj4string" not in val
    )


def ser_val(val):
    if val is None:
        return "NULL"
    if isinstance(val, dict):
        classes = val.get("class", ())
        if isinstance(classes, str):
            classes = (classes,)
        if "crs" in classes:
            if is_na_crs(val):
                return "NACRS"
            inp = val.get("input")
            wkt = val.get("wkt")
            return "CRS\x1f" + ("NA" if inp is None else esc(inp)) + "\x1f" + (
                "NA" if wkt is None else esc(wkt)
            )
        if "crs_parameters" in classes:
            return ser_par(val)
        if tuple(classes) == ("list",) and all(key == "class" for key in val):
            return "LIST"
    if isinstance(val, str):
        return "CHR\x1f" + esc(val)
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, int):
        return "INT\x1f" + str(val)
    if isinstance(val, float):
        if math.isnan(val):
            return "NA"
        return "DBL\x1f" + format(val, ".17g")
    return "OTHER\x1f" + esc(repr(val))


def token(label, fn):
    buf = io.StringIO()
    caught = []
    err = None
    val = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with contextlib.redirect_stderr(buf):
                val = fn()
    except Exception as exc:
        err = str(exc)
    warned = [str(item.message).rstrip("\r\n") for item in caught]
    messages = [line for line in buf.getvalue().splitlines() if line != ""]
    body = "ERR\x1f" + esc(err) if err is not None else ser_val(val)
    if warned:
        body += "\x1fW:" + "\x1e".join(esc(item) for item in warned)
    if messages:
        body += "\x1fM:" + "\x1e".join(esc(item) for item in messages)
    return label + "\x1f" + body


crs4326 = st_crs(4326)
merc = st_crs("+proj=merc")
sfc4326 = {"class": ("sfc_POINT", "sfc"), "crs": crs4326}
sf4326 = {"class": ("sf", "data.frame"), "sf_column": "geom", "geom": sfc4326}
bb = {
    "class": ("bbox",),
    "xmin": 0.0,
    "ymin": 0.0,
    "xmax": 0.0,
    "ymax": 0.0,
    "crs": crs4326,
}
bb0 = {"class": ("bbox",), "xmin": 0.0, "ymin": 0.0, "xmax": 1.0, "ymax": 1.0}
old_sfc = {
    "class": ("sfc",),
    "crs": {"class": ("crs",), "epsg": 4326, "proj4string": "+proj=longlat"},
}
old_na = {
    "class": ("sfc",),
    "crs": {"class": ("crs",), "epsg": float("nan"), "proj4string": "+proj=longlat"},
}
null_sfc = {"class": ("sfc",)}
na_sfc = {"class": ("sfc",), "crs": {"class": ("crs",), "input": None, "wkt": None}}
bad_sf = {"class": ("sf", "data.frame"), "sf_column": "geom", "a": 1}
no_col = {"class": ("sf", "data.frame"), "a": 1}
crs_plain = {"class": ("CRS",), "projargs": "+proj=longlat", "comment": None}
crs_named = {"class": ("CRS",), "projargs": "+proj=longlat", "comment": crs4326["wkt"]}
crs_unknown = {"class": ("CRS",), "projargs": "+proj=merc", "comment": merc["wkt"]}
sfc3857 = {"class": ("sfc",), "crs": st_crs(3857)}


def one():
    return [
        token("int", lambda: st_crs(4326)),
        token("dbl", lambda: st_crs(4326.0)),
        token("half", lambda: st_crs(4326.5)),
        token("epsg", lambda: st_crs("EPSG:3857")),
        token("p4", lambda: st_crs("+proj=longlat +datum=WGS84")),
        token("ogc", lambda: st_crs("OGC:CRS84")),
        token("merc", lambda: st_crs("+proj=merc")),
        token("badproj", lambda: st_crs("+proj=ll")),
        token("big", lambda: st_crs(999999)),
        token("zero", lambda: st_crs(0)),
        token("nan", lambda: st_crs(float("nan"))),
        token("inf", lambda: st_crs(float("inf"))),
        token("ninf", lambda: st_crs(float("-inf"))),
        token("null", lambda: st_crs(None)),
        token("true", lambda: st_crs(True)),
        token("false", lambda: st_crs(False)),
        token("empty", lambda: st_crs("")),
        token("wgs", lambda: st_crs("WGS84")),
        token("len2", lambda: st_crs(np.array([4326.0, 3857.0]))),
        token("num0", lambda: st_crs(np.array([], dtype=float))),
        token("ch0", lambda: st_crs(np.array([], dtype="U"))),
        token("ch2", lambda: st_crs(np.array(["EPSG:4326", "EPSG:3857"]))),
        token("wktback", lambda: st_crs(crs4326["wkt"])),
        token("mercback", lambda: st_crs(merc["wkt"])),
        token("din", lambda: crs_get(st_crs("EPSG:3857"), "input")),
        token("dp4", lambda: crs_get(st_crs(3857), "proj4string")),
        token("dname", lambda: crs_get(st_crs(4326), "Name")),
        token("depsg", lambda: crs_get(st_crs(3857), "epsg")),
        token("sfc", lambda: st_crs(sfc4326)),
        token("sf", lambda: st_crs(sf4326)),
        token("bbox", lambda: st_crs(bb)),
        token("bbox0", lambda: st_crs(bb0)),
        token("crsobj", lambda: st_crs(crs4326)),
        token("old", lambda: st_crs(old_sfc)),
        token("oldna", lambda: st_crs(old_na)),
        token("mat", lambda: st_crs(np.array([[4326.0]]))),
        token("badsf", lambda: st_crs(bad_sf)),
        token("nocol", lambda: st_crs(no_col)),
        token("nullcrs", lambda: st_crs(null_sfc)),
        token("nullpar", lambda: st_crs(null_sfc, parameters=True)),
        token("napar", lambda: st_crs(na_sfc, parameters=True)),
        token("parign", lambda: st_crs(4326, parameters=True)),
        token("p4326", lambda: st_crs(sfc4326, parameters=True)),
        token("p3857", lambda: st_crs(sfc3857, parameters=True)),
        token("crs0", lambda: st_crs(crs_plain)),
        token("crs4326", lambda: st_crs(crs_named)),
        token("crsmerc", lambda: st_crs(crs_unknown)),
        token("lst", lambda: st_crs([1])),
        token("df", lambda: st_crs({"class": ("data.frame",), "a": 1})),
        token("bigd", lambda: st_crs(1e20)),
        token("compound", lambda: st_crs("EPSG:4326+5703")),
        token("init", lambda: st_crs("+init=epsg:4326")),
        token("raster", lambda: st_crs({"class": ("Raster",)})),
        token("spatial", lambda: st_crs({"class": ("Spatial",)})),
        token("spat", lambda: st_crs({"class": ("SpatRaster",)})),
        token("ob", lambda: st_crs("+proj=ob_tran +o_proj=longlat +o_lat_p=90 +o_lon_p=0")),
    ]


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append(time.perf_counter() - t0)
print("VALUE")
print("\n".join(value))
print("END")
print(f"MS {statistics.median(elapsed) * 1000:.17g}")

ex_in = crs_get(st_crs("EPSG:3857"), "input")
ex_p4 = crs_get(st_crs(3857), "proj4string")
with open("/home/ahmed/killr_projects/killr/packages/sf/docs/output/st_crs-python.txt", "w", encoding="utf-8") as handle:
    handle.write(f'st_crs("EPSG:3857")$input returns {ex_in}.\n')
    handle.write(f"st_crs(3857)$proj4string returns {ex_p4}.\n")
