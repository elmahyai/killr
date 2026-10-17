
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/backports")
from backports import *
from backports._values import NA

def flat(x):
    if x is None:
        return "null"
    if x is NA or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (list, tuple)):
        return "|".join(flat(item) for item in x)
    if isinstance(x, float):
        if math.isfinite(x) and x.is_integer():
            return str(int(x))
        return format(x, ".10g")
    return str(x)


def one():
    obj = as_rconcordance_default("<!-- concordance::Sample.Rmd:1 9 1 1 6 14 1 -->")
    printed = print_rconcordance(obj)
    return [printed.src_file, str(len(printed.src_line)), str(printed.src_line[19])]
value = one()
if not isinstance(value, str):
    value = flat(value)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
