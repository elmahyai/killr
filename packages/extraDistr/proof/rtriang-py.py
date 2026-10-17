import statistics
import time

from boot.rng import set_seed
from extradistr.closed import rtriang

set_seed(1)
value = rtriang(4, 0, 4, 1)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rtriang(4, 0, 4, 1)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
