import statistics
import time

from xts import isOrdered

def one():
    return isOrdered(range(1, 11))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("TRUE" if value is True else "FALSE" if value is False else value)
print("%.17g" % statistics.median(elapsed))
