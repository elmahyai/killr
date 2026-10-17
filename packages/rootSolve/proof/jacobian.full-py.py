import statistics
import time

from rootSolve import jacobian_full


def model(time, y, parms):
    return [-0.1 * y[0] + 0.02 * y[1], 0.1 * y[0] - 0.2 * y[1]]


y = {"A": 1.0, "B": 2.0}


def one():
    return jacobian_full(y, model)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
