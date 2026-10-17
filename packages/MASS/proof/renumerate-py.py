import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/Formula")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass.denumerate import denumerate
from mass.renumerate import renumerate_deparse


def one():
    f = denumerate("~(1 + 2 + 3)^3 + a/b")
    return renumerate_deparse(f)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
