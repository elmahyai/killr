import statistics
import time
import numpy as np
from quantreg.dynrq import dynrq, ts_series
UK = "/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/uk_driver_deaths.txt"
AP = "/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/air_passengers.txt"
uk = ts_series(np.log10(np.loadtxt(UK)), start=(1969, 1), frequency=12)
ap = ts_series(np.log(np.loadtxt(AP)), start=(1949, 1), frequency=12)
data_uk = {"uk": uk}
data_ap = {"ap": ap}

import warnings
from quantreg.dynrq import summary_dynrqs
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    d3 = dynrq("uk ~ L(uk, 1) + L(uk, 12)", data_uk, tau=[0.25, 0.5, 0.75])
def one():
    pieces = summary_dynrqs(d3, se="nid")
    return np.concatenate([np.asarray(p["coefficients"], dtype=float).ravel(order="F") for p in pieces])

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

value = one()
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(",".join(f"{item:.17g}" for item in array))
print(f"{statistics.median(elapsed):.17g}")
