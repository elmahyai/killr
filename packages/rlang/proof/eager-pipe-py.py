import statistics
import sys
import time

from rlang.eager_pipe import eager_pipe, force_lazy


def one():
    eager_pipe("x", 1)
    return force_lazy(sys._getframe().f_locals["x"])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
