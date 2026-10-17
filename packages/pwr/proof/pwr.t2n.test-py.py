import statistics
import time

from pwr import pwr_t2n_test

def one():
    return pwr_t2n_test(d=0.6, n1=90, n2=60, alternative="greater")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
