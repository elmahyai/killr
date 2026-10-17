import statistics
import time

from nortest import ad_test

x = [2.1, 3.4, float("nan"), 1.2, 5.6, 4.0, 3.3, 2.8, 6.1, 1.9, float("nan"), 4.4]


def one():
    return ad_test(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
