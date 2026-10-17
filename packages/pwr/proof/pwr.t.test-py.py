import statistics
import time

from pwr import pwr_t_test

def one():
    return pwr_t_test(d=2 / 2.8, n=30, sig_level=0.05, type="two.sample", alternative="two.sided")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
