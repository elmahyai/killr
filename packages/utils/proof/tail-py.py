import statistics
import time

from utils import tail


def one():
    return ",".join(str(value) for value in tail(list(range(1, 11))))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
