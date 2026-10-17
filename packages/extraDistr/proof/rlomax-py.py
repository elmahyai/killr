import statistics
import time

from boot.rng import set_seed
from extradistr.closed import rlomax

set_seed(1)
value = rlomax(4, 1.5, 2.5)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rlomax(4, 1.5, 2.5)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
