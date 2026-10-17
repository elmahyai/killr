import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/ordinal")

import numpy as np

from boot.rng import set_seed
from ordinal.rgumbel import rgumbel


def one():
    set_seed(12345)
    return rgumbel(6, location=1.0, scale=2.0, max=False)


value = np.ravel(np.asarray(one(), dtype=float), order="F")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (
        ",".join("%.17g" % float(x) for x in value),
        statistics.median(elapsed),
    )
)
