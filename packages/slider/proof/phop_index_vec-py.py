
import json, math, statistics, time
from slider import *
x = [1, 5, 3, 2, 6, 10]
y = [2, 4, 1, 3, 5, 7]
i = [0, 1, 3, 4, 6, 8]
ch = ["a", "b", "c", "d", "e", "f"]
lg = [True, False, True, True, False, True]
def flat(value):
    if value and isinstance(value[0], list):
        out = []
        for item in value:
            out.extend(flat(item) if item else [])
        return out
    out = []
    for item in value:
        if isinstance(item, bool):
            out.append(int(item))
        elif isinstance(item, float) and math.isnan(item):
            out.append(None)
        else:
            out.append(item)
    return out

def one():
    return flat(phop_index_vec([x, y], i, [0, 4], [6, 8], lambda a, b: sum(a)/len(a)))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
