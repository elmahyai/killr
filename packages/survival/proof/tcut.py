import math
import statistics
import time

from survival.tcut import levels, tcut


def _fmt(values):
    out = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            out.append("NA")
        else:
            out.append(f"{float(value):.17g}")
    return out


def serialize(x):
    vals = _fmt(x.values.tolist())
    cuts = _fmt(x.cutpoints.tolist())
    labs = list(x.labels)
    return [
        "|".join(vals),
        "|".join(cuts),
        "|".join(labs),
        "|".join(levels(x)),
    ]


def one():
    x = [55, 65, 75, 85, float("nan"), 72.5]
    a = tcut(x, [0, 60, 70, 80, 100], ["<=60", "60-70", "70-80", ">80"])
    b = tcut([1, 2, 3, 4, 5], 3)
    cobj = tcut([10, 20], [0, 15, 30], scale=2)
    d = a[[0, 2, 4, 5]]
    out = []
    for item in (a, b, cobj, d):
        out.extend(serialize(item))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
