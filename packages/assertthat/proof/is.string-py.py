import statistics
import time
from assertthat import is_string
from assertthat.objects import NA

def one():
    return [is_string(1), is_string("a"), is_string(["a", "b"]), is_string(True), is_string(None), is_string(NA), is_string(float("inf"))]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
