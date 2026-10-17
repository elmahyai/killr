import statistics
import time

from utils import localeToCharset


def one():
    return " ".join(localeToCharset("en_US.UTF-8"))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
