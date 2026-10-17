import statistics
import time

from pwr import pwr_norm_test

def one():
    return pwr_norm_test(d=(105 - 100) / 15, n=20, sig_level=0.05, alternative="greater")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
