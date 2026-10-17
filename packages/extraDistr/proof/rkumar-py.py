import statistics
import time

from boot.rng import set_seed
from extradistr.closed import rkumar

set_seed(1)
value = rkumar(4, 2, 3)
print(",".join("%.17g" % float(v) for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rkumar(4, 2, 3)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
