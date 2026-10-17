import statistics
import time

from pwr import pwr_anova_test

def one():
    return pwr_anova_test(f=0.28, k=4, n=20, sig_level=0.05)["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
