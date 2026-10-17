import statistics
import time

from extradistr.closed import pfrechet

value = pfrechet([0.5, 1, 2, 4], 1.5, 0, 1)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    pfrechet([0.5, 1, 2, 4], 1.5, 0, 1)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
