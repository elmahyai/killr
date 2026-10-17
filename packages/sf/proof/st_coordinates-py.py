import math
import os
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/sf")

from sf.st_coordinates import st_coordinates

outer = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]
hole = [[1.0, 1.0], [1.0, 2.0], [2.0, 2.0], [2.0, 1.0], [1.0, 1.0]]
outer12 = [[x + 12.0, y + 12.0] for x, y in outer]
zring = [[0.0, 0.0, 1.0], [10.0, 0.0, 2.0], [10.0, 10.0, 3.0], [0.0, 10.0, 4.0], [0.0, 0.0, 5.0]]
suite = [
    [0.5, -0.5],
    [1.5, -1.5],
    [2.5, -2.5],
    [1.25, -1.25],
    [1.35, -1.35],
    [0.05, -0.05],
    [1.23456789, -1.23456789],
    [0.04, -0.04],
    [-0.0, 0.0],
    [None, float("nan")],
    [float("inf"), float("-inf")],
]
long = [[i, 2001 - i] for i in range(1, 2001)]


def pt(xy, dim="XY"):
    return {"class": (dim, "POINT", "sfg"), "xy": xy}


def ln(xy, dim="XY"):
    return {"class": (dim, "LINESTRING", "sfg"), "xy": xy}


def mp(xy, dim="XY"):
    return {"class": (dim, "MULTIPOINT", "sfg"), "xy": xy}


def poly(xy, dim="XY"):
    return {"class": (dim, "POLYGON", "sfg"), "xy": xy}


def mls(xy, dim="XY"):
    return {"class": (dim, "MULTILINESTRING", "sfg"), "xy": xy}


def mpoly(xy, dim="XY"):
    return {"class": (dim, "MULTIPOLYGON", "sfg"), "xy": xy}


def sfc(kind, geoms, precision=0):
    return {"class": (f"sfc_{kind}", "sfc"), "geoms": geoms, "precision": precision}


def sf(geom):
    return {"class": ("sf", "data.frame"), "sf_column": "geom", "geom": geom}


named = pt([1.0, 2.0])
int_line = ln([[1, 4], [2, 5], [3, 6]])
prec10 = sfc("POINT", [pt([1.234, 1.234])], precision=10)
prec_na = sfc("POINT", [pt([1.25, -1.25])], precision=float("nan"))
prec_null = {"class": ("sfc_POINT", "sfc"), "geoms": [pt([1.25, -1.25])]}
bad_mp = mpoly([[], [outer]])
unequal = sfc("POINT", [pt([1, 2]), pt([3, 4, 5], "XYZ")])
short = sfc("POINT", [pt([5])])
zero_pt = sfc("POINT", [pt([])])
special = pt([-0.0, None, float("nan"), float("inf")], "XYZM")

obj_pts = sfc("POINT", [pt([1.234, 5.0]), pt([-2.0, 0.0])])
obj_ints = sfc("POINT", [pt([1, 2]), pt([3, 4])])
obj_named = sfc("POINT", [named])
obj_z = sfc("POINT", [pt([1.0, 2.0, 9.0], "XYZ")])
obj_m = sfc("POINT", [pt([1.0, 2.0, 9.0], "XYM")])
obj_zm = sfc("POINT", [pt([1.0, 2.0, 3.0, 4.0], "XYZM")])
obj_na = sfc("POINT", [pt([None, 1.0])])
obj_nan = sfc("POINT", [pt([float("nan"), 1.0])])
obj_neg0 = sfc("POINT", [pt([-0.0, 0.0])])
obj_emptypt = sfc("POINT", [pt([None, None])])
obj_lines = sfc("LINESTRING", [ln(outer), ln(hole)])
obj_emptyline = sfc("LINESTRING", [ln([]), ln([[1.0, 2.0], [3.0, 4.0]])])
obj_twoline0 = sfc("LINESTRING", [ln([]), ln([])])
obj_mp = sfc("MULTIPOINT", [mp([[1.0, 0.0], [4.0, 3.0], [2.0, -1.0]]), mp([[7.0, 8.0]])])
obj_poly = sfc("POLYGON", [poly([outer, hole])])
obj_twopoly = sfc("POLYGON", [poly([outer]), poly([hole])])
obj_polyz = sfc("POLYGON", [poly([zring], "XYZ")])
obj_poly0 = sfc("POLYGON", [poly([]), poly([])])
obj_ring0 = sfc("POLYGON", [poly([[]])])
obj_ringthen = sfc("POLYGON", [poly([[], outer])])
obj_mpoly = sfc("MULTIPOLYGON", [mpoly([[outer, hole], [outer12]])])
obj_twompoly = sfc("MULTIPOLYGON", [mpoly([[outer]]), mpoly([[hole]])])
obj_mpoly0 = sfc("MULTIPOLYGON", [mpoly([]), mpoly([])])
obj_mls = sfc("MULTILINESTRING", [mls([outer, hole])])
obj_mls0 = sfc("MULTILINESTRING", [mls([])])
obj_zline = sfc("LINESTRING", [ln([[1.0, 2.0, 100.0], [4.0, -5.0, -100.0]], "XYZ")])
obj_xym = sfc("MULTIPOINT", [mp([[1.0, 2.0, 7.0], [4.0, -5.0, 8.0]], "XYM")])
obj_intline = sfc("LINESTRING", [int_line])
obj_intround = sfc("LINESTRING", [int_line], precision=10)
obj_sfg = pt([1.0, 2.0])
obj_sfground = ln([[1.234, 1.234]])
obj_sf = sf(sfc("POINT", [pt([0, 1]), pt([1, 2])]))
obj_sfround = sf(prec10)
obj_empty = sfc("GEOMETRY", [])
obj_plain = sfc("POINT", [pt([1.234, 1.234])])
obj_r100 = sfc("POINT", [pt([1.234, 1.234])], precision=100)
obj_s10 = sfc("LINESTRING", [ln(suite)], precision=10)
obj_s100 = sfc("LINESTRING", [ln(suite)], precision=100)
obj_s01 = sfc("LINESTRING", [ln(suite)], precision=0.1)
obj_sneg = sfc("LINESTRING", [ln(suite)], precision=-1)
obj_sp10 = sfc("POINT", [special], precision=10)
obj_spneg = sfc("POINT", [special], precision=-1)
obj_long = sfc("LINESTRING", [ln(long)])
obj_gc = sfc("GEOMETRYCOLLECTION", [pt([1, 2])])
obj_mixed = {"class": ("sfc_GEOMETRY", "sfc"), "geoms": [pt([1, 2]), ln([[1, 3], [2, 4]])], "precision": 0}
obj_tri = sfc("TRIANGLE", [{"class": ("XY", "TRIANGLE", "sfg"), "xy": [outer]}])
obj_bad = {"class": ("sf", "data.frame"), "sf_column": "geom", "a": 1}
obj_nocol = {"class": ("sf", "data.frame"), "a": 1}
obj_badmp = sfc("MULTIPOLYGON", [bad_mp])


def _is_r_na(z):
    bits = np.array(z, dtype=np.float64).view(np.uint64)
    return int(bits) & 0xFFFFFFFF == 1954


def fmt_num(z, integer=False):
    if integer:
        return str(int(z))
    z = float(z)
    if _is_r_na(z):
        return "NA"
    if math.isnan(z):
        return "NaN"
    if math.isinf(z):
        return "Inf" if z > 0 else "-Inf"
    if z == 0.0 and math.copysign(1.0, z) < 0.0:
        return "-0"
    return format(z, ".17g")


def show_mat(val):
    integer = np.issubdtype(val.data.dtype, np.integer)
    if val.logical or val.data.dtype == np.bool_:
        kind = "logical"
    elif integer:
        kind = "integer"
    else:
        kind = "double"
    cn_s = "" if val.colnames is None else "|".join(val.colnames)
    flat = val.data.ravel(order="F")
    nums = "" if flat.size == 0 else ",".join(fmt_num(z, integer) for z in flat)
    return f"{kind}/{val.nrow}x{val.ncol}/{cn_s}/{nums}"


def token(fn):
    warned = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                val = fn()
            finally:
                warned = [str(item.message) for item in caught]
    except Exception as exc:
        body = "ERR " + str(exc).replace("\n", "\\n")
    else:
        body = show_mat(val)
    if warned:
        body += "|" + "|".join(item.replace("\n", "\\n") for item in warned)
    return body


def one():
    parts = [
        "pts=" + token(lambda: st_coordinates(obj_pts)),
        "ints=" + token(lambda: st_coordinates(obj_ints)),
        "named=" + token(lambda: st_coordinates(obj_named)),
        "z=" + token(lambda: st_coordinates(obj_z)),
        "m=" + token(lambda: st_coordinates(obj_m)),
        "zm=" + token(lambda: st_coordinates(obj_zm)),
        "na=" + token(lambda: st_coordinates(obj_na)),
        "nan=" + token(lambda: st_coordinates(obj_nan)),
        "neg0=" + token(lambda: st_coordinates(obj_neg0)),
        "emptypt=" + token(lambda: st_coordinates(obj_emptypt)),
        "lines=" + token(lambda: st_coordinates(obj_lines)),
        "emptyline=" + token(lambda: st_coordinates(obj_emptyline)),
        "twoline0=" + token(lambda: st_coordinates(obj_twoline0)),
        "mp=" + token(lambda: st_coordinates(obj_mp)),
        "poly=" + token(lambda: st_coordinates(obj_poly)),
        "twopoly=" + token(lambda: st_coordinates(obj_twopoly)),
        "polyz=" + token(lambda: st_coordinates(obj_polyz)),
        "poly0=" + token(lambda: st_coordinates(obj_poly0)),
        "ring0=" + token(lambda: st_coordinates(obj_ring0)),
        "ringthen=" + token(lambda: st_coordinates(obj_ringthen)),
        "mpoly=" + token(lambda: st_coordinates(obj_mpoly)),
        "twompoly=" + token(lambda: st_coordinates(obj_twompoly)),
        "mpoly0=" + token(lambda: st_coordinates(obj_mpoly0)),
        "mls=" + token(lambda: st_coordinates(obj_mls)),
        "mls0=" + token(lambda: st_coordinates(obj_mls0)),
        "zline=" + token(lambda: st_coordinates(obj_zline)),
        "xym=" + token(lambda: st_coordinates(obj_xym)),
        "intline=" + token(lambda: st_coordinates(obj_intline)),
        "intround=" + token(lambda: st_coordinates(obj_intround, round=True)),
        "sfg=" + token(lambda: st_coordinates(obj_sfg)),
        "sfground=" + token(lambda: st_coordinates(obj_sfground, round=True)),
        "sf=" + token(lambda: st_coordinates(obj_sf)),
        "sfround=" + token(lambda: st_coordinates(obj_sfround, round=True)),
        "empty=" + token(lambda: st_coordinates(obj_empty)),
        "plain=" + token(lambda: st_coordinates(obj_plain)),
        "r10=" + token(lambda: st_coordinates(prec10, round=True)),
        "rfalse=" + token(lambda: st_coordinates(prec10, round=False)),
        "r100=" + token(lambda: st_coordinates(obj_r100, round=True)),
        "r0=" + token(lambda: st_coordinates(prec10, round=0)),
        "r2=" + token(lambda: st_coordinates(prec10, round=2)),
        "pos=" + token(lambda: st_coordinates(prec10, True)),
        "s10=" + token(lambda: st_coordinates(obj_s10, round=True)),
        "s100=" + token(lambda: st_coordinates(obj_s100, round=True)),
        "s01=" + token(lambda: st_coordinates(obj_s01, round=True)),
        "sneg=" + token(lambda: st_coordinates(obj_sneg, round=True)),
        "sp10=" + token(lambda: st_coordinates(obj_sp10, round=True)),
        "spneg=" + token(lambda: st_coordinates(obj_spneg, round=True)),
        "long=" + token(lambda: st_coordinates(obj_long)),
        "gc=" + token(lambda: st_coordinates(obj_gc)),
        "mixed=" + token(lambda: st_coordinates(obj_mixed)),
        "tri=" + token(lambda: st_coordinates(obj_tri)),
        "bad=" + token(lambda: st_coordinates(obj_bad)),
        "nocol=" + token(lambda: st_coordinates(obj_nocol)),
        "null=" + token(lambda: st_coordinates(None)),
        "dbl=" + token(lambda: st_coordinates(1.5)),
        "chr=" + token(lambda: st_coordinates("a")),
        "logi=" + token(lambda: st_coordinates(True)),
        "lst=" + token(lambda: st_coordinates([1])),
        "badmp=" + token(lambda: st_coordinates(obj_badmp)),
        "unequal=" + token(lambda: st_coordinates(unequal)),
        "short=" + token(lambda: st_coordinates(short)),
        "zeropt=" + token(lambda: st_coordinates(zero_pt)),
        "naprec=" + token(lambda: st_coordinates(prec_na, round=True)),
        "nullprec=" + token(lambda: st_coordinates(prec_null, round=True)),
        "rvec=" + token(lambda: st_coordinates(prec10, round=[True, False])),
        "rna=" + token(lambda: st_coordinates(prec10, round=float("nan"))),
        "rstr=" + token(lambda: st_coordinates(prec10, round="TRUE")),
    ]
    return ";".join(parts)


def cell(mat):
    row = mat.data[0]
    return " ".join(f"{name} {fmt_num(value)}" for name, value in zip(mat.colnames, row))


ex = sfc("POINT", [pt([1.234, 1.234])])
m1 = st_coordinates(ex)
m2 = st_coordinates(sfc("POINT", [pt([1.234, 1.234])], precision=10), round=True)
m3 = st_coordinates(sfc("POINT", [pt([1.234, 1.234])], precision=100), round=True)
example = [
    f"st_coordinates(x) returns {cell(m1)}.",
    f"st_coordinates(x, round = TRUE) with precision 10 returns {cell(m2)}.",
    f"st_coordinates(x, round = TRUE) after units::set_units(1, cm) returns {cell(m3)}.",
]
out = "/home/ahmed/killr_projects/killr/packages/sf/docs/output/st_coordinates-python.txt"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(example) + "\n")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
