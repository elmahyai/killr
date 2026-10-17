import statistics
import time

from utils import RMatrix, tail


def one():
    bottom = tail(RMatrix(list(range(1, 13)), 4, 3), 2)
    parts = [",".join(str(value) for value in bottom.data)]
    for margin in bottom.dimnames or []:
        if margin is not None:
            parts.extend(margin)
    return "|".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
