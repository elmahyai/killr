import statistics
import time
from rootSolve import steady_band

def decay(t, y, p):
    return [[-0.1 * value for value in y]]

def one():
    return steady_band([1.0, 2.0, 3.0, 4.0], func=decay, nspec=1).y

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
