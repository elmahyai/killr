import statistics
import time

from pwr import ES_w1

def one():
    p0 = [0.25, 0.25, 0.25, 0.25]
    share = (1 - 0.375) / 3
    return ES_w1(p0, [0.375, share, share, share])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
