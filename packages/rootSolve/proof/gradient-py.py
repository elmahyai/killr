import math
import statistics
import time

from rootSolve import gradient


def logistic(x, times):
    n0, rate, carrying = x["N0"], x["r"], x["K"]
    return [carrying / (1 + (carrying - n0) / n0 * math.exp(-rate * t)) for t in times]


x = {"N0": 76.1, "r": 0.02, "K": 500}


def one():
    return gradient(logistic, x, times=list(range(6)))


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
