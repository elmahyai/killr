import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowmeans2 import rowMeans2

flat = np.fromfile(Path(__file__).with_name("means2-x.bin"), dtype="<f8")
x = np.reshape(flat, (400, 250), order="F")

def one():
    rowMeans2(x, na_rm=False, refine=True)

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
