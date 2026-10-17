import statistics
import time

import numpy as np

from ordinal import dlgamma


def one():
    return dlgamma(np.array([-1.0, 0.0, 1.0]), -0.4, log=True)

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
