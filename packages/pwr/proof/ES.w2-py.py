import statistics
import time

from pwr import ES_w2

def one():
    return ES_w2([[0.225, 0.125, 0.125, 0.125], [0.16, 0.16, 0.04, 0.04]])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
