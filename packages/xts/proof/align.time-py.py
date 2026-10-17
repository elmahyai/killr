import statistics
import time

from datetime import datetime, timezone
from xts import align_time

def one():
    base = datetime(2020, 1, 1, 0, 0, 10, tzinfo=timezone.utc).timestamp()
    return ",".join(format(value, ".17g") for value in align_time([base + offset for offset in range(6)], 10))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("TRUE" if value is True else "FALSE" if value is False else value)
print("%.17g" % statistics.median(elapsed))
