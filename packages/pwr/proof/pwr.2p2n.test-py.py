import statistics
import time

from pwr import pwr_2p2n_test

def one():
    return pwr_2p2n_test(h=0.30, n1=80, n2=245, sig_level=0.05, alternative="greater")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
