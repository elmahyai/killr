import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/sf")

import sf.st_bbox as bbox_mod
from sf.st_bbox import st_bbox
from sf.st_is_longlat import _st_crs

crs4326 = _st_crs(4326)
bbox_mod._full_bbox()

outer = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]
hole = [[1.0, 1.0], [1.0, 2.0], [2.0, 2.0], [2.0, 1.0], [1.0, 1.0]]
outer12 = [[x + 12.0, y + 12.0] for x, y in outer]

example_sfc = {
    "class": ("sfc_POINT", "sfc"),
    "crs": crs4326,
    "bbox": {"class": ("bbox",), "xmin": 0.0, "ymin": 1.0, "xmax": 1.0, "ymax": 2.0},
}
example_sf = {"class": ("sf", "data.frame"), "sf_column": "geom", "geom": example_sfc}
nums = {
    "class": ("numeric",),
    "values": [16.1, 16.6, 48.6, 47.9],
    "names": ["xmin", "xmax", "ymax", "ymin"],
}
point = {"class": ("XY", "POINT", "sfg"), "xy": [1.0, 2.0]}
pointz = {"class": ("XYZ", "POINT", "sfg"), "xy": [1.0, 2.0, 9.0]}
pointna = {"class": ("XY", "POINT", "sfg"), "xy": [None, None]}
partial = {"class": ("XY", "POINT", "sfg"), "xy": [None, 3.0]}
mp = {"class": ("XY", "MULTIPOINT", "sfg"), "xy": [[1.0, 0.0], [4.0, 3.0], [2.0, -1.0]]}
ls = {"class": ("XY", "LINESTRING", "sfg"), "xy": [[0.0, 1.0], [5.0, -2.0], [3.0, 4.0]]}
poly = {"class": ("XY", "POLYGON", "sfg"), "xy": [outer, hole]}
poly0 = {"class": ("XY", "POLYGON", "sfg"), "xy": []}
polyring0 = {"class": ("XY", "POLYGON", "sfg"), "xy": [[]]}
full = {
    "class": ("XY", "POLYGON", "sfg"),
    "xy": [[[0.0, -90.0], [0.0, -90.0]]],
}
mpoly = {"class": ("XY", "MULTIPOLYGON", "sfg"), "xy": [[outer, hole], [outer12]]}
mpoly0 = {"class": ("XY", "MULTIPOLYGON", "sfg"), "xy": [[], [outer]]}
mls = {"class": ("XY", "MULTILINESTRING", "sfg"), "xy": [outer, hole]}
ls0 = {"class": ("XY", "LINESTRING", "sfg"), "xy": []}
mp0 = {"class": ("XY", "MULTIPOINT", "sfg"), "xy": []}
line_14 = {"class": ("XY", "LINESTRING", "sfg"), "xy": [[1.0, 3.0], [2.0, 4.0]]}
gc = {
    "class": ("XY", "GEOMETRYCOLLECTION", "sfg"),
    "xy": [{"class": ("XY", "POINT", "sfg"), "xy": [1.0, 2.0]}, line_14],
}
gc0 = {"class": ("XY", "GEOMETRYCOLLECTION", "sfg"), "xy": []}
gcmix = {
    "class": ("XY", "GEOMETRYCOLLECTION", "sfg"),
    "xy": [ls0, {"class": ("XY", "POINT", "sfg"), "xy": [-1.0, 4.0]}],
}
gcinf = {
    "class": ("XY", "GEOMETRYCOLLECTION", "sfg"),
    "xy": [{"class": ("XY", "POINT", "sfg"), "xy": [1.0, None]}],
}
tri = {"class": ("XY", "TRIANGLE", "sfg"), "xy": [outer]}
tin = {"class": ("XY", "TIN", "sfg"), "xy": [[outer], [hole]]}
id_bb = st_bbox(point)
bb4326 = st_bbox(
    {"class": ("numeric",), "values": [1.0, 2.0, 3.0, 4.0], "names": ["xmin", "ymin", "xmax", "ymax"]},
    crs=4326,
)
sfc_stored = {
    "class": ("sfc_POINT", "sfc"),
    "crs": crs4326,
    "bbox": {"class": ("bbox",), "xmin": 9.0, "ymin": 8.0, "xmax": 7.0, "ymax": 6.0},
}
sf_stored = {"class": ("sf", "data.frame"), "sf_column": "geom", "geom": sfc_stored}
reorder = {
    "class": ("numeric",),
    "values": [4.0, 1.0, 9.0, 3.0, 2.0],
    "names": ["ymax", "xmin", "junk", "xmax", "ymin"],
}
miss = {"class": ("numeric",), "values": [1.0, 2.0], "names": ["xmin", "ymin"]}
noname = {"class": ("numeric",), "values": [1.0, 2.0, 3.0, 4.0], "names": None}
dup = {
    "class": ("numeric",),
    "values": [1.0, 9.0, 2.0, 3.0, 4.0],
    "names": ["xmin", "xmin", "ymin", "xmax", "ymax"],
}
ints = {
    "class": ("integer", "numeric"),
    "values": [1, 2, 3, 4],
    "names": ["xmin", "ymin", "xmax", "ymax"],
}
nax = {
    "class": ("numeric",),
    "values": [None, 1.0, 2.0, 3.0],
    "names": ["xmin", "ymin", "xmax", "ymax"],
}
extra = {
    "class": ("numeric",),
    "values": [1.5, -2.0, 3.25, 4.0, 100.0],
    "names": ["xmin", "ymin", "xmax", "ymax", "extra"],
}
nums4 = {
    "class": ("numeric",),
    "values": [1.0, 2.0, 3.0, 4.0],
    "names": ["xmin", "ymin", "xmax", "ymax"],
}
spatial = {"class": ("Spatial",)}
raster = {"class": ("Raster",)}
extent = {"class": ("Extent",)}
spatr = {"class": ("SpatRaster",)}
spatv = {"class": ("SpatVector",)}
spate = {"class": ("SpatExtent",)}
szero = {"class": ("XY", "LINESTRING", "sfg"), "xy": [[-0.0, 0.0], [0.0, -0.0]]}
mpna = {"class": ("XY", "MULTIPOINT", "sfg"), "xy": [[None, 1.0], [None, 2.0]]}
mpnan = {"class": ("XY", "MULTIPOINT", "sfg"), "xy": [[float("nan"), 1.0], [float("nan"), 2.0]]}
short = {"class": ("XY", "POINT", "sfg"), "xy": [5.0]}
msurf = {"class": ("XY", "MULTISURFACE", "sfg"), "xy": [poly]}
ccurve = {
    "class": ("XY", "COMPOUNDCURVE", "sfg"),
    "xy": [{"class": ("XY", "LINESTRING", "sfg"), "xy": [[0.0, 0.0], [1.0, 1.0]]}],
}
long = {
    "class": ("XY", "LINESTRING", "sfg"),
    "xy": [[float(i), float(2001 - i)] for i in range(1, 2001)],
}
zls = {"class": ("XYZ", "LINESTRING", "sfg"), "xy": [[1.0, 2.0, 100.0], [4.0, -5.0, -100.0]]}
polythen = {"class": ("XY", "POLYGON", "sfg"), "xy": [[], outer]}
mpone = {"class": ("XY", "MULTIPOINT", "sfg"), "xy": [[7.0, 8.0]]}
nobbox = {"class": ("sfc_POINT", "sfc"), "crs": crs4326, "bbox": None}
nocrs = {
    "class": ("sfc_POINT", "sfc"),
    "crs": None,
    "bbox": {"class": ("bbox",), "xmin": 1.0, "ymin": 2.0, "xmax": 1.0, "ymax": 2.0},
}
sfbad = {"class": ("sf", "data.frame"), "sf_column": "geom", "a": 1}
sfcol = {"class": ("sf", "data.frame"), "a": 1}
mat = np.array([[1, 2], [3, 4]])
fac = {"class": ("factor",)}
gcfull = {"class": ("XY", "GEOMETRYCOLLECTION", "sfg"), "xy": [full]}
na_then = {"class": ("XY", "LINESTRING", "sfg"), "xy": [[None, 1.0], [2.0, 3.0]]}
circ = {"class": ("XY", "CIRCULARSTRING", "sfg"), "xy": [[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]]}
circ2 = {
    "class": ("XY", "CIRCULARSTRING", "sfg"),
    "xy": [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]],
}
circ0 = {"class": ("XY", "CIRCULARSTRING", "sfg"), "xy": []}
empty = {"class": ("double", "numeric"), "values": [], "names": []}


def fmt_num(z):
    if z is None:
        return "NA"
    if isinstance(z, float) and math.isnan(z):
        return "NaN"
    if z == math.inf:
        return "Inf"
    if z == -math.inf:
        return "-Inf"
    return format(float(z), ".17g")


def crs_token(crs):
    if crs is None:
        return "NULL"
    if isinstance(crs, dict) and crs.get("input") is None and crs.get("wkt") is None:
        return "NA"
    if isinstance(crs, dict):
        return "NA" if crs.get("input") is None else str(crs["input"])
    return "NULL"


def show_bb(val):
    classes = tuple(val.get("class", ()))
    if "bbox" not in classes:
        crs = val["crs"] if "crs" in val else None
        return "LIST/" + crs_token(crs)
    crs = val["crs"] if "crs" in val else None
    nums = ",".join(fmt_num(val[name]) for name in ("xmin", "ymin", "xmax", "ymax"))
    return nums + "/" + crs_token(crs)


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
        body = show_bb(val)
    if warned:
        body += "|" + "|".join(item.replace("\n", "\\n") for item in warned)
    return body


def full_off_call():
    old = bbox_mod._USE_S2
    bbox_mod._USE_S2 = False
    try:
        return st_bbox(full)
    finally:
        bbox_mod._USE_S2 = old


def one():
    parts = [
        "sf=" + token(lambda: st_bbox(example_sf)),
        "num=" + token(lambda: st_bbox(nums, crs=crs4326)),
        "point=" + token(lambda: st_bbox(point)),
        "pointz=" + token(lambda: st_bbox(pointz)),
        "pointna=" + token(lambda: st_bbox(pointna)),
        "partial=" + token(lambda: st_bbox(partial)),
        "mp=" + token(lambda: st_bbox(mp)),
        "ls=" + token(lambda: st_bbox(ls)),
        "poly=" + token(lambda: st_bbox(poly)),
        "poly0=" + token(lambda: st_bbox(poly0)),
        "polyring0=" + token(lambda: st_bbox(polyring0)),
        "full=" + token(lambda: st_bbox(full)),
        "fulloff=" + token(full_off_call),
        "mpoly=" + token(lambda: st_bbox(mpoly)),
        "mpoly0=" + token(lambda: st_bbox(mpoly0)),
        "mls=" + token(lambda: st_bbox(mls)),
        "ls0=" + token(lambda: st_bbox(ls0)),
        "mp0=" + token(lambda: st_bbox(mp0)),
        "gc=" + token(lambda: st_bbox(gc)),
        "gc0=" + token(lambda: st_bbox(gc0)),
        "gcmix=" + token(lambda: st_bbox(gcmix)),
        "gcinf=" + token(lambda: st_bbox(gcinf)),
        "tri=" + token(lambda: st_bbox(tri)),
        "tin=" + token(lambda: st_bbox(tin)),
        "id=" + token(lambda: st_bbox(id_bb)),
        "idcrs=" + token(lambda: st_bbox(bb4326)),
        "sfc=" + token(lambda: st_bbox(sfc_stored)),
        "sfstore=" + token(lambda: st_bbox(sf_stored)),
        "reorder=" + token(lambda: st_bbox(reorder)),
        "miss=" + token(lambda: st_bbox(miss)),
        "noname=" + token(lambda: st_bbox(noname)),
        "dup=" + token(lambda: st_bbox(dup)),
        "int=" + token(lambda: st_bbox(ints)),
        "nax=" + token(lambda: st_bbox(nax)),
        "extra=" + token(lambda: st_bbox(extra)),
        "pos=" + token(lambda: st_bbox(nums4, 4326)),
        "crsna=" + token(lambda: st_bbox(nums4, crs=None)),
        "chr=" + token(lambda: st_bbox("nope")),
        "null=" + token(lambda: st_bbox(None)),
        "logi=" + token(lambda: st_bbox(True)),
        "spatial=" + token(lambda: st_bbox(spatial)),
        "raster=" + token(lambda: st_bbox(raster)),
        "extent=" + token(lambda: st_bbox(extent)),
        "spatr=" + token(lambda: st_bbox(spatr)),
        "spatv=" + token(lambda: st_bbox(spatv)),
        "spate=" + token(lambda: st_bbox(spate)),
        "szero=" + token(lambda: st_bbox(szero)),
        "mpna=" + token(lambda: st_bbox(mpna)),
        "mpnan=" + token(lambda: st_bbox(mpnan)),
        "short=" + token(lambda: st_bbox(short)),
        "msurf=" + token(lambda: st_bbox(msurf)),
        "ccurve=" + token(lambda: st_bbox(ccurve)),
        "long=" + token(lambda: st_bbox(long)),
        "zls=" + token(lambda: st_bbox(zls)),
        "polythen=" + token(lambda: st_bbox(polythen)),
        "mpone=" + token(lambda: st_bbox(mpone)),
        "nobbox=" + token(lambda: st_bbox(nobbox)),
        "nocrs=" + token(lambda: st_bbox(nocrs)),
        "sfbad=" + token(lambda: st_bbox(sfbad)),
        "sfcol=" + token(lambda: st_bbox(sfcol)),
        "mat=" + token(lambda: st_bbox(mat)),
        "one=" + token(lambda: st_bbox(1)),
        "factor=" + token(lambda: st_bbox(fac)),
        "lst=" + token(lambda: st_bbox([1])),
        "df=" + token(lambda: st_bbox({"class": ("data.frame",)})),
        "gcfull=" + token(lambda: st_bbox(gcfull)),
        "nathen=" + token(lambda: st_bbox(na_then)),
        "circ=" + token(lambda: st_bbox(circ)),
        "circ2=" + token(lambda: st_bbox(circ2)),
        "circ0=" + token(lambda: st_bbox(circ0)),
        "empty=" + token(lambda: st_bbox(empty)),
    ]
    return ";".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
