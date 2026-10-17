import statistics
import time
from assertthat import is_number
from assertthat.objects import NA, NA_real_

def one():
    return [is_number(1), is_number(-1), is_number(1.5), is_number(list(range(1, 6))), is_number("a"), is_number(True), is_number(None), is_number(NA), is_number(NA_real_), is_number(float("inf")), is_number(float("-inf"))]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
