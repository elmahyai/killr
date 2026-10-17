import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/farver")
from farver.decode_colour import decode_colour
from farver.convert_colour import convert_colour
from farver.encode_colour import encode_colour

def flat(value):
    if isinstance(value, list):
        return ",".join("NA" if item is None else str(item) for item in value)
    array = np.asarray(value, dtype=np.float64)
    parts = []
    for item in array.ravel(order="F"):
        parts.append("NA" if not np.isfinite(item) else format(float(item), ".16g"))
    return ",".join(parts)

spectrum = decode_colour(["#FF0000","#FF9900","#CCFF00","#33FF00","#00FF66","#00FFFF","#0066FF","#3300FF","#CC00FF","#FF0099"])
spectrum_hcl = convert_colour(spectrum, "rgb", "hcl")
def one():
    return flat(encode_colour(spectrum)) + "|" + flat(encode_colour(spectrum, alpha=[0.5, 1])) + "|" + flat(encode_colour(spectrum_hcl, from_="hcl"))

one()
elapsed = []
value = None
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
