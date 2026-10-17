import statistics
import time
from pathlib import Path

import numpy as np

from ordinal._clm_rho import clm_like_from_npz
from ordinal.nominal_test import nominal_test, nominal_test_values

_RHO = Path(__file__).resolve().parent / "slice_wine_rho.npz"


def one():
    obj = clm_like_from_npz(str(_RHO))
    return nominal_test_values(nominal_test(obj))


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
