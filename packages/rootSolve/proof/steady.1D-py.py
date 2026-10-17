import statistics
import time
from rootSolve import steady_1d

def g(t, y, p):
    n = len(y)
    rate = [0.0] * n
    rate[0] = y[1] - y[0]
    for i in range(1, n - 1):
        rate[i] = y[i - 1] - 2 * y[i] + y[i + 1]
    rate[-1] = 1 - y[-1]
    return [rate]

def one():
    return steady_1d([0.2] * 5, func=g, nspec=1).y

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
