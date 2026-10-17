import statistics
import time

from rlang.hash import hash
from rlang.na_or import Double


def one():
    return hash(Double([1.0, 2.0, 3.0]))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
