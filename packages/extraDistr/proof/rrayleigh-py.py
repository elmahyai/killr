import statistics
import time

from boot.rng import set_seed
from extradistr.closed import rrayleigh

set_seed(1)
value = rrayleigh(4, 2)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rrayleigh(4, 2)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
