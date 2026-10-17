import statistics
import time

from pwr import ES_h, pwr_p_test

def one():
    return pwr_p_test(h=ES_h(0.5, 0.4), n=60, sig_level=0.05, alternative="two.sided")["power"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
