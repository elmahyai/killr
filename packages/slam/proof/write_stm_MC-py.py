import statistics
import tempfile
from pathlib import Path

import numpy as np

from slam import *
from slam._arrays import as_array, as_matrix


def one():
    folder = Path(tempfile.mkdtemp())
    stem = folder / "mc"
    m = simple_triplet_matrix([1, 2, 1], [1, 1, 2], [1.5, 2, 3], 2, 2)
    write_stm_MC(m, stem)
    parts = []
    for suffix in ("_dim", "_row_ccs", "_col_ccs", "_tfn_nz"):
        parts.append("\n".join((folder / ("mc" + suffix)).read_text().splitlines()))
    text = "\n".join(parts)
    return np.array([ord(ch) for ch in text], dtype=float)

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
