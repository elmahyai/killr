import statistics
import tempfile
from pathlib import Path

import numpy as np

from slam import *
from slam._arrays import as_array, as_matrix


def one():
    folder = Path(tempfile.mkdtemp())
    stem = folder / "mc"
    (folder / "mc_dim").write_text("2 2 3\n")
    (folder / "mc_row_ccs").write_text("0\n1\n0\n")
    (folder / "mc_col_ccs").write_text("0\n2\n3\n")
    (folder / "mc_tfn_nz").write_text("1.5\n3\n2\n")
    return np.ravel(as_matrix(read_stm_MC(stem)), order="F")

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
