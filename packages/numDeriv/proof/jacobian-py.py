import statistics
import time

import numpy as np

from numderiv import jacobian


def one():
    def func2(x):
        return np.concatenate([np.sin(x), np.cos(x)])

    return np.ravel(jacobian(func2, np.arange(2) * 2 * np.pi), order="F")


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
