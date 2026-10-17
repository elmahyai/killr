import statistics
import time
from assertthat import not_empty
from assertthat.assertions import frame
from assertthat.objects import NA

def one():
    return [not_empty(1), not_empty([]), not_empty(frame(0, 11)), not_empty(frame(32, 0)), not_empty(NA), not_empty(None)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
