import statistics
import time

from extradistr.closed import dgompertz

value = dgompertz([0, 0.5, 1, 2], 1.2, 0.4)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dgompertz([0, 0.5, 1, 2], 1.2, 0.4)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
