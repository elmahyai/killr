import statistics
import time

from pwr import plot_power_htest, pwr_t_test

def one():
    curve = plot_power_htest(pwr_t_test(d=0.3, power=0.8, type="two.sample"), draw=False)
    return ",".join(format(value, ".17g") for value in curve["power"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
