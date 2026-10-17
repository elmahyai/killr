import statistics
import tempfile
from pathlib import Path

import numpy as np

from slam import *
from slam._arrays import as_array, as_matrix


def one():
    a = simple_sparse_zero_array([2, 3])
    return np.concatenate([a.dim, [a.v.size]])

value = np.ravel(np.asarray(one(), dtype=float), order="F")
elapsed = []
for _ in range(20):
    started = __import__("time").perf_counter()
    one()
    elapsed.append((__import__("time").perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (
        ",".join("%.17g" % float(part) for part in value),
        statistics.median(elapsed),
    )
)
