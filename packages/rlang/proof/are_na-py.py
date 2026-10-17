import statistics
import time

from rlang.are_na import are_na
from rlang.na_or import NA, NA_REAL, Double, Integer


def _show(vec):
    return ",".join("TRUE" if item else "FALSE" for item in vec.values)


def one():
    left = _show(are_na(Double([1.0, 2.0, NA_REAL])))
    right = _show(are_na(Integer([1, NA, 3])))
    return left + " " + right


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
