import statistics
import time
from assertthat import is_scalar
from assertthat.objects import NA

def one():
    return [is_scalar(1), is_scalar(list(range(1, 6))), is_scalar("a"), is_scalar(["a", "b"]), is_scalar(True), is_scalar([True, False]), is_scalar(None), is_scalar(NA), is_scalar(float("inf"))]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
