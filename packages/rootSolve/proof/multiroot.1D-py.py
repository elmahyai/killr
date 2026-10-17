import statistics
import time
from rootSolve import multiroot_1d

def chain(x):
    rate = [0.0] * len(x)
    rate[0] = x[1] - x[0]
    for i in range(1, len(x) - 1):
        rate[i] = x[i - 1] - 2 * x[i] + x[i + 1]
    rate[-1] = 1 - x[-1]
    return rate

def one():
    return multiroot_1d(chain, [0.2] * 5, nspec=1).root

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
