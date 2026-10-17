import statistics
import time

from datetime import datetime, timezone
start = datetime(2020, 1, 15, tzinfo=timezone.utc).timestamp()
idx = [start + index * 86400 for index in range(41)]
from xts import nyears

def one():
    return nyears(idx)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("TRUE" if value is True else "FALSE" if value is False else value)
print("%.17g" % statistics.median(elapsed))
