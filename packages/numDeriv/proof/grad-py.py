import statistics
import time

import numpy as np

from numderiv import grad


def one():
    return np.ravel(grad(np.sin, np.arange(11) * 2 * np.pi / 10), order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
