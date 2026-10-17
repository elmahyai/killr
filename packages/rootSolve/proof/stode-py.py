import statistics
import time
from rootSolve import stode

def fun(t, y, p):
    return [[-0.1 * y[0] + 0.02 * y[1], 0.1 * y[0] - 0.2 * y[1]]]

def one():
    return stode([1.0, 1.0], func=fun).y

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
