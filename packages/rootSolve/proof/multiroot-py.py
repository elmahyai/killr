import statistics
import time
from rootSolve import multiroot

def model(x):
    return [x[0] ** 2 + x[1] ** 2 - 1, x[0] ** 2 - x[1] ** 2 + 0.5]

def one():
    return multiroot(model, [1.0, 1.0]).root

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
