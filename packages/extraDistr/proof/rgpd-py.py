import statistics
import time

from boot.rng import set_seed
from extradistr.closed import rgpd

set_seed(1)
value = rgpd(4, 0, 1, 0.25)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rgpd(4, 0, 1, 0.25)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
