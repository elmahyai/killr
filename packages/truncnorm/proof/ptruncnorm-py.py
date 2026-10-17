from truncnorm import ptruncnorm

def one():
    return ",".join(f"{v:.17g}" for v in ptruncnorm([-2, 0, 2], -1, 1))

import statistics
import time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + str(value).replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
