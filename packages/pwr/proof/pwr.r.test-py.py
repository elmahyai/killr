import statistics
import time

from pwr import pwr_r_test

def one():
    return pwr_r_test(r=0.3, n=50, sig_level=0.05, alternative="two.sided")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
