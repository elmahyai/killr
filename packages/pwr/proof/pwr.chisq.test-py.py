import statistics
import time

from pwr import pwr_chisq_test

def one():
    return pwr_chisq_test(w=0.289, df=3, N=100, sig_level=0.05)["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
