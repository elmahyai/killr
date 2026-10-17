
import json, math, statistics, time
from datetime import date, timedelta

from slider.pslide_period_lgl import pslide_period_lgl
from warp import Date

n = 2000
days = [date(2010, 1, 1) + timedelta(days=d) for d in range(n)]
i = Date(days)
x = [k % 7 == 0 for k in range(1, n + 1)]
y = [k % 11 == 0 for k in range(1, n + 1)]

def vtype(values):
    kinds = set()
    for v in values:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            if isinstance(v, float):
                kinds.add("double")
            continue
        if isinstance(v, bool):
            kinds.add("logical")
        elif isinstance(v, int):
            kinds.add("integer")
        elif isinstance(v, float):
            kinds.add("double")
        elif isinstance(v, str):
            kinds.add("character")
    if not kinds:
        return "logical"
    if len(kinds) != 1:
        raise SystemExit("mixed element types: %s" % sorted(kinds))
    return kinds.pop()


def clean(values):
    return [None if (isinstance(v, float) and math.isnan(v)) else v for v in values]


def one():
    return pslide_period_lgl([x, y], i, "month", lambda a, b: any(a) and any(b), before=1, complete=True)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"type": vtype(value), "value": clean(value), "median_ms": statistics.median(elapsed)}))
