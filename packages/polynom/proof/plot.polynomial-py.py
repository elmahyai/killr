import matplotlib
matplotlib.use("Agg")
from polynom import polynomial, plot_polynomial

def one():
    return ",".join(f"{v:.17g}" for v in plot_polynomial(polynomial([1, 2, 1]), xlim=[0, 1], len_=5)[1])

import statistics, time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter(); one(); elapsed.append((time.perf_counter()-started)*1000)
print("VALUE " + str(value))
print(f"MS {statistics.median(elapsed):.17g}")
