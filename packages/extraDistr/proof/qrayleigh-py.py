import statistics
import time

from extradistr.closed import qrayleigh

value = qrayleigh([0.1, 0.3, 0.5, 0.8], 2)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    qrayleigh([0.1, 0.3, 0.5, 0.8], 2)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
