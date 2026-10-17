import statistics
import time

from extradistr.closed import dpower

value = dpower([0.5, 1, 1.5, 2.5], 3, 2)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dpower([0.5, 1, 1.5, 2.5], 3, 2)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
