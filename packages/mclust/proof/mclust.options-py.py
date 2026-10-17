import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.mclust_options import mclust_options


def one():
    opt = mclust_options()
    mclust_options(subset=2500)
    s1 = mclust_options("subset")
    mclust_options(opt)
    s2 = mclust_options("subset")
    return [float(s1), float(s2)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
