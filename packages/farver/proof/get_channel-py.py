import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/farver")
from farver.get_channel import get_channel

def flat(value):
    if isinstance(value, list):
        return ",".join("NA" if item is None else str(item) for item in value)
    array = np.asarray(value, dtype=np.float64)
    parts = []
    for item in array.ravel(order="F"):
        parts.append("NA" if not np.isfinite(item) else format(float(item), ".16g"))
    return ",".join(parts)

spectrum = ["#FF0000","#FF9900","#CCFF00","#33FF00","#00FF66","#00FFFF","#0066FF","#3300FF","#CC00FF","#FF0099"]
def one():
    return flat(get_channel(spectrum, "r")) + "|" + flat(get_channel(spectrum, "l", space="lab")) + "|" + flat(get_channel(spectrum, "alpha"))

one()
elapsed = []
value = None
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
