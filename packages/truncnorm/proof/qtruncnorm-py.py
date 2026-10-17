from truncnorm import qtruncnorm

def one():
    vals = qtruncnorm([0.25, 0.5, 0.9], [-1, float("-inf"), -1], [2, 1, float("inf")])
    return ",".join(f"{v:.17g}" for v in vals)

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
