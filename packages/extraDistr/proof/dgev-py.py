import statistics
import time

from extradistr.closed import dgev

value = dgev([-1, 0, 1, 2], 0, 1, -0.2)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dgev([-1, 0, 1, 2], 0, 1, -0.2)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
