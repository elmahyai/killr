import statistics
import time

import numpy as np

from ordinal import qgumbel


def one():
    return qgumbel(np.array([0.2, 0.8]), location=1.0, scale=2.0, lower_tail=False, max=False)

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
