import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ordinal.drop_coef import drop_coef


def _soup_design():
    """Same PRODID * DAY model matrix as the R proof (fixed soup rows)."""
    # Built once from ordinal::soup via model.matrix(~ PRODID * DAY, data = soup).
    rows = np.load(Path(__file__).resolve().parent / "drop_coef_soup_X.npz")
    return rows["X"]


def one():
    x = _soup_design()
    new_x = drop_coef(x, silent=True)
    rank = int(np.linalg.matrix_rank(new_x))
    return np.concatenate(
        [
            np.array([x.shape[1], new_x.shape[1], rank], dtype=float),
            np.ravel(new_x, order="F"),
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
    % (
        ",".join("%.17g" % float(v) for v in value),
        statistics.median(elapsed),
    )
)
