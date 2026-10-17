import statistics
import time

from pwr import cohen_ES

def one():
    return cohen_ES(test="r", size="medium")["effect.size"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
