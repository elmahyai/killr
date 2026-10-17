from truncnorm import vtruncnorm

def one():
    vals = [vtruncnorm(-1, 1)[0], vtruncnorm(8, 9)[0], vtruncnorm(2, float("inf"), 0, 2)[0]]
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
