import statistics
import time

from pwr import pwr_2p_test

def one():
    return pwr_2p_test(h=0.3, n=80, sig_level=0.05, alternative="greater")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
