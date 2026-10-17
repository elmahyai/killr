import statistics
import time

from extradistr.closed import ppareto

value = ppareto([1, 2, 3, 5], 2, 1)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    ppareto([1, 2, 3, 5], 2, 1)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
