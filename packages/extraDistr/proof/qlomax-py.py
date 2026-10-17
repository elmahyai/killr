import statistics
import time

from extradistr.closed import qlomax

value = qlomax([0.1, 0.3, 0.5, 0.8], 1.5, 2.5)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    qlomax([0.1, 0.3, 0.5, 0.8], 1.5, 2.5)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
