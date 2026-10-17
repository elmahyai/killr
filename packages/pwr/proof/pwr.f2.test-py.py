import statistics
import time

from pwr import pwr_f2_test

def one():
    return pwr_f2_test(u=5, v=89, f2=0.1 / 0.9, sig_level=0.05)["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
