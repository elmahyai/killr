import statistics
import time

from utils import RMatrix, head


def one():
    return ",".join(str(value) for value in head(RMatrix(list(range(1, 13)), 4, 3), 2).data)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
