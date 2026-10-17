import statistics
import time

from rootSolve import hessian


def squares(x):
    return sum(value * value for value in x)


x = {"a": 1.0, "b": -3.0}


def one():
    return hessian(squares, x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
