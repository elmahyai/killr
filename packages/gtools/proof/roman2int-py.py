import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.roman2int import roman2int


def flat(value) -> str:
    if value is None:
        return ""
    arr = np.atleast_1d(np.asarray(value, dtype=np.float64))
    parts = []
    for item in arr.ravel(order="C"):
        if np.isnan(item):
            parts.append("NA")
        else:
            parts.append(f"{float(item):.16g}")
    return ",".join(parts)


def one() -> str:
    val3899 = "MMMDCCCXCIX"
    val3900 = "MMMCM"
    val4000 = "MMMM"
    parts = [
        flat(roman2int(["I", "V", "X", "C", "L", "D", "M"])),
        flat(roman2int("MMXVI")),
        flat(roman2int("mmxvi")),
        flat(roman2int(val3899)),
        flat(roman2int(val3900)),
        flat(roman2int(val4000)),
        flat(roman2int(["  iv  ", "MCMLXXXIV", "invalid", "", float("nan"), "IXX"])),
        flat(roman2int(["CDXLIV", "CMXCIX", "MMCDXLIV"])),
    ]
    return ",".join(parts)


roman2int("I")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
