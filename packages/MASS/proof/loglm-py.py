import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")

from mass.loglm import loglm


class _Table(np.ndarray):
    pass


def one():
    data = np.array([[10.0, 20.0], [30.0, 40.0]])
    data = data.view(_Table)
    data._dimnames = ["A", "B"]
    fm = loglm("~ A + B", data)
    return np.array([fm.lrt, fm.pearson, fm.df, float(fm.nobs)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
