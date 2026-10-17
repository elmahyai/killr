import statistics
import time

from utils.at_names import AtNames, S4


def one():
    obj = S4("TestS4AtNames", a=1, b="x")
    return ",".join(AtNames(obj, ""))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
