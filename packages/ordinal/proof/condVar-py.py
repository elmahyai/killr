import statistics
import time
from pathlib import Path

import numpy as np

from ordinal.cond_var import clmm_cond_var_like_from_npz, cond_var, cond_var_values

_NPZ = Path(__file__).resolve().parent / "condVar_wine_clmm.npz"


def one():
    obj = clmm_cond_var_like_from_npz(str(_NPZ))
    return cond_var_values(cond_var(obj))


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
