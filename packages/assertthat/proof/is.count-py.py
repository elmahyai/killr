import statistics
import time
from assertthat import is_count
from assertthat.objects import NA, NA_integer_, NA_real_

def one():
    return [is_count(1), is_count(-1), is_count(1.5), is_count(list(range(1, 6))), is_count("a"), is_count(True), is_count(None), is_count(NA), is_count(NA_real_), is_count(NA_integer_), is_count(float("nan")), is_count(float("inf")), is_count(float("-inf")), is_count(1e10 + 0.0001), is_count(1e10 - 0.1)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
