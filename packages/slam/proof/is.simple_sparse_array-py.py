import statistics
import tempfile
from pathlib import Path

import numpy as np

from slam import *
from slam._arrays import as_array, as_matrix


def one():
    return np.array([float(is_simple_sparse_array(simple_sparse_array([[1, 1]], [1], [1, 1])))])

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
