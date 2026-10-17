import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/Formula")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass.denumerate import denumerate_deparse


def one():
    return denumerate_deparse("~(1 + 2 + 3)^3 + a/b")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
