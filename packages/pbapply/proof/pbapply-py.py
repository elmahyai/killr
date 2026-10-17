import json
import statistics
import time

import numpy as np

from pbapply.pbapply import pbapply
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        m = np.arange(1, 13, dtype=float).reshape(3, 4, order="F")
        row_sums = pbapply(m, 1, sum)
        col_means = pbapply(m, 2, np.mean)
        return [float(v) for v in row_sums] + [float(v) for v in col_means]
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
