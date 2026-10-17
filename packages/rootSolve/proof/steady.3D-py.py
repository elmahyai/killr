import statistics
import time
from rootSolve import steady_3d

def approach(t, y, p):
    return [[1.0 - value for value in y]]

def one():
    return steady_3d([0.0] * 8, func=approach, dimens=(2, 2, 2)).y

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
