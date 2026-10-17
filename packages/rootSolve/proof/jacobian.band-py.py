import statistics
import time

from rootSolve import jacobian_band


def decay(time, y, parms):
    return [-0.1 * value for value in y]


y = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}


def one():
    return jacobian_band(y, decay)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
