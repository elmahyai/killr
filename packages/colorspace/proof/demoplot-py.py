import json
import statistics
import time

from colorspace.demoplot import demoplot_palette_use
from colorspace.diverging_hcl import diverging_hcl


def _block(raw: dict) -> dict:
    out = {"type": raw["type"], "colors": raw["colors"]}
    if "matrix" in raw:
        out["matrix"] = raw["matrix"]
    if "matrix_shape" in raw:
        out["matrix_shape"] = raw["matrix_shape"]
    if "border_black" in raw:
        out["border_black"] = raw["border_black"]
    return out


def one():
    x7 = diverging_hcl(7)
    x1 = diverging_hcl(1)
    types = (
        "map",
        "heatmap",
        "scatter",
        "spine",
        "bar",
        "pie",
        "perspective",
        "mosaic",
        "lines",
    )
    out = {name: _block(demoplot_palette_use(x7, name)) for name in types}
    out["perspective_single"] = _block(demoplot_palette_use(x1, "perspective"))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
