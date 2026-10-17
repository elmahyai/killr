import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowcummaxs import rowCummaxs

flat = np.fromfile(Path(__file__).with_name("rowcummaxs-x.bin"), dtype="<f8")
x = np.reshape(flat, (400, 250), order="F")

def one():
    rowCummaxs(x)

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
