import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/farver")
from farver.decode_colour import decode_colour
from farver.convert_colour import convert_colour
from farver.compare_colour import compare_colour

def flat(value):
    if isinstance(value, list):
        return ",".join("NA" if item is None else str(item) for item in value)
    array = np.asarray(value, dtype=np.float64)
    parts = []
    for item in array.ravel(order="F"):
        parts.append("NA" if not np.isfinite(item) else format(float(item), ".16g"))
    return ",".join(parts)

r = decode_colour(["#FF0000","#FF9900","#CCFF00","#33FF00","#00FF66","#00FFFF","#0066FF","#3300FF","#CC00FF","#FF0099"])
h = decode_colour(["#FF0000","#FF1700","#FF2E00","#FF4600","#FF5D00","#FF7400","#FF8B00","#FFA200","#FFB900","#FFD100","#FFE800","#FFFF00","#FFFF2A","#FFFF80","#FFFFD5"])
h_luv = convert_colour(h, "rgb", "luv")
def one():
    return flat(compare_colour(r, h, "rgb", method="cie2000")) + "|" + flat(compare_colour(r, from_space="rgb", method="cmc")) + "|" + flat(compare_colour(r, h_luv, "rgb", "luv"))

one()
elapsed = []
value = None
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
