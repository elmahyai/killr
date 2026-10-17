import statistics
import time
from assertthat import are_equal
from assertthat.objects import NA

def one():
    return [are_equal(2, 1.9), are_equal(2, 1.999, tol=0.01), are_equal(2, 2), are_equal("a", "a"), are_equal("a", "b"), are_equal(NA, NA), are_equal(None, None)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
