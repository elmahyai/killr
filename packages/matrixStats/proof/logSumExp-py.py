import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.logsumexp import logSumExp

lx = np.fromfile(Path(__file__).with_name("logSumExp-lx.bin"), dtype=np.float64)

def one():
    return logSumExp(lx, na_rm=False)

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"{one():.17g}")
print(statistics.median(elapsed))
