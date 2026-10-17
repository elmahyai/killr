import statistics
import time
from rootSolve import runsteady

def approach(t, y, p):
    return [[1.0 - value for value in y]]

def one():
    return runsteady([0.0], func=approach, times=[0, float('inf')]).y

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
