import statistics
import time

import numpy as np

from numderiv import hessian


def one():
    def func(x):
        return x[0] ** 2 + 3 * x[0] * x[1] + x[1] ** 2

    return np.ravel(hessian(func, [1.0, 1.0]), order="F")


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
