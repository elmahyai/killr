import statistics
import time

from extradistr.closed import dgumbel

value = dgumbel([-1, 0, 1, 2], 0.5, 1.5)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dgumbel([-1, 0, 1, 2], 0.5, 1.5)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
