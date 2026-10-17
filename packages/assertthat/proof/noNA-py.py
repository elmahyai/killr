import statistics
import time
from assertthat import no_na
from assertthat.objects import NA

def one():
    return [no_na("a"), no_na([True, NA]), no_na(list(range(1, 1001))), no_na(None)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
