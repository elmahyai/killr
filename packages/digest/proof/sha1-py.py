import statistics
import time

from digest.serialize import real
from digest.sha1 import sha1


def one():
    return sha1(real([1, 2, 3]))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
