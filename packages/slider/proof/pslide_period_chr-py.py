
import json, statistics, time
from datetime import date, timedelta

from slider.pslide_period_chr import pslide_period_chr
from warp import Date

n = 2000
days = [date(2010, 1, 1) + timedelta(days=d) for d in range(n)]
i = Date(days)
x = [chr(ord("a") + ((k) % 26)) for k in range(n)]
y = [chr(ord("a") + ((k + 13) % 26)) for k in range(n)]


def one():
    return pslide_period_chr(
        [x, y],
        i,
        "month",
        lambda a, b: "".join(a) + "|" + "".join(b),
        before=1,
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
