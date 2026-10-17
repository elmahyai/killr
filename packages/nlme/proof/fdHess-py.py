import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.fdhess import fdHess


def one():
    def fun(x):
        return x[0] * (1 - np.exp(-0.4 * x[1]))

    result = fdHess([12.3, 2.34], fun)
    return np.concatenate(
        [
            np.atleast_1d(np.asarray(result["mean"], dtype=float)),
            np.atleast_1d(np.asarray(result["gradient"], dtype=float)),
            np.ravel(np.asarray(result["Hessian"], dtype=float), order="F"),
        ]
    )


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
