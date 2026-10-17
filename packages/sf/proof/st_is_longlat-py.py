import statistics
import sys
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/sf")

from sf.st_is_longlat import _st_crs, st_is_longlat

crs4326 = _st_crs(4326)
crs3857 = _st_crs(3857)
na_crs = {"class": ("crs",), "input": None, "wkt": None}
bad = {
    "class": ("sfc",),
    "crs": crs4326,
    "bbox": {"xmin": -181, "ymin": 0, "xmax": 10, "ymax": 10, "class": ("bbox",)},
}
good = {
    "class": ("sfc",),
    "crs": _st_crs(4326),
    "bbox": {"xmin": 1, "ymin": 2, "xmax": 1, "ymax": 2, "class": ("bbox",)},
}
wild = {
    "class": ("sfc",),
    "crs": crs3857,
    "bbox": {"xmin": -181, "ymin": 0, "xmax": 10, "ymax": 10, "class": ("bbox",)},
}
na_bb = {
    "class": ("sfc",),
    "crs": crs4326,
    "bbox": {"xmin": -181, "ymin": None, "xmax": 10, "ymax": 10, "class": ("bbox",)},
}
empty = {
    "class": ("sfc",),
    "crs": na_crs,
    "bbox": {"xmin": 0, "ymin": 0, "xmax": 0, "ymax": 0, "class": ("bbox",)},
}
geom = {
    "class": ("sfc",),
    "crs": crs4326,
    "bbox": {"xmin": -181, "ymin": 0, "xmax": 10, "ymax": 10, "class": ("bbox",)},
}
sf_bad = {"class": ("sf", "data.frame"), "sf_column": "geom", "geom": geom}
wkt = crs4326["wkt"]


def token(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        val = fn()
    if val is None:
        shown = "NA"
    elif val is True:
        shown = "TRUE"
    elif val is False:
        shown = "FALSE"
    else:
        shown = str(val)
    if caught:
        return shown + "|" + str(caught[0].message)
    return shown


def one():
    return [
        token(lambda: st_is_longlat(4326)),
        token(lambda: st_is_longlat(3857)),
        token(lambda: st_is_longlat(4978)),
        token(lambda: st_is_longlat(4979)),
        token(lambda: st_is_longlat(float("nan"))),
        token(lambda: st_is_longlat("+proj=longlat +datum=WGS84")),
        token(lambda: st_is_longlat("+proj=merc")),
        token(lambda: st_is_longlat("OGC:CRS84")),
        token(lambda: st_is_longlat("EPSG:4326+5703")),
        token(lambda: st_is_longlat(bad)),
        token(lambda: st_is_longlat(good)),
        token(lambda: st_is_longlat(wild)),
        token(lambda: st_is_longlat(na_bb)),
        token(lambda: st_is_longlat(empty)),
        token(lambda: st_is_longlat(sf_bad)),
        token(lambda: st_is_longlat("+proj=ob_tran +o_proj=longlat +o_lat_p=90 +o_lon_p=0")),
        token(lambda: st_is_longlat(999999)),
        token(lambda: st_is_longlat(None)),
        token(lambda: st_is_longlat(True)),
        token(lambda: st_is_longlat(crs4326)),
        token(lambda: st_is_longlat(wkt)),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + ",".join(value))
print(f"MS {statistics.median(elapsed):.17g}")
