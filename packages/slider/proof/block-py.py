
import json, statistics, time
from datetime import date, timedelta

from slider.block import block
from warp import Date

x = list(range(1, 7))
days = [date(2019, 1, 1) + timedelta(days=d) for d in (-2, -1, 0, 1, 2, 31)]
i = Date(days)


def flat(value):
    if value and isinstance(value[0], list):
        out = []
        for item in value:
            out.extend(flat(item) if item else [])
        return out
    out = []
    for item in value:
        out.append(item)
    return out


def one():
    return flat(block(x, i, period="year"))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
