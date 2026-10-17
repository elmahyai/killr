import statistics
import time
from assertthat import is_flag
from assertthat.objects import NA

def one():
    return [is_flag(1), is_flag("a"), is_flag(True), is_flag(False), is_flag([True, False]), is_flag(None), is_flag(NA), is_flag(float("inf"))]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
