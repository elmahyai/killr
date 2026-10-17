import statistics
import time

from utils import checkHT


def one():
    checkHT(6, None)
    return "TRUE"


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
