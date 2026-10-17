
import json, math, statistics, time
from datetime import date, timedelta

import numpy as np
from slider.slide_period2 import slide_period2
from warp import Date

n = 2000
days = [date(2010, 1, 1) + timedelta(days=d) for d in range(n)]
i = Date(days)
x = np.arange(1, n + 1, dtype=float)
y = np.arange(101, n + 101, dtype=float)


def flat(value):
    if value is None:
        return [None]
    if isinstance(value, list):
        if not value:
            return []
        if isinstance(value[0], list):
            out = []
            for item in value:
                out.extend(flat(item) if item else [])
            return out
        out = []
        for item in value:
            out.extend(flat(item))
        return out
    out = []
    if isinstance(value, bool):
        out.append(int(value))
    elif isinstance(value, float) and math.isnan(value):
        out.append(None)
    else:
        out.append(value)
    return out


def one():
    return flat(
        slide_period2(
            x,
            y,
            i,
            "month",
            lambda a, b: float(np.sum(a) + np.sum(b)),
            before=1,
        )
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
