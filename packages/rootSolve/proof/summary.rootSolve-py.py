import statistics
import time
from rootSolve import steady_1d, summary_rootsolve

def decay(t, y, p):
    return [[-value for value in y]]

out = steady_1d([0.0, 1.0, 3.0], func=decay, nspec=1)

def one():
    return list(summary_rootsolve(out).columns['1'].values())

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
