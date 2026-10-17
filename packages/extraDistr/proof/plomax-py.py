import statistics
import time

from extradistr.closed import plomax

value = plomax([0.2, 1, 2, 5], 1.5, 2.5)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    plomax([0.2, 1, 2, 5], 1.5, 2.5)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
