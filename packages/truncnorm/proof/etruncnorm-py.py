from truncnorm import etruncnorm

def one():
    vals = [etruncnorm(-1, 1)[0], etruncnorm(8, 9)[0], etruncnorm(1, float("inf"))[0], etruncnorm(-20, 0)[0]]
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
