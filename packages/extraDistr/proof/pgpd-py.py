import statistics
import time

from extradistr.closed import pgpd

value = pgpd([0.5, 1, 2, 4], 0, 1, 0.25)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    pgpd([0.5, 1, 2, 4], 0, 1, 0.25)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
