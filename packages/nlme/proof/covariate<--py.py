import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.covariate_setter import covariate_assign
from nlme.getcovariate import getCovariate
from nlme.var_power import initialize, varPower


def one():
    data = {
        "y": [1, 2, 3, 4, 5, 6],
        "x": [1.2, 2.5, 3.1, 4.0, 5.5, 6.3],
    }
    vf = varPower(0.35, form="~x")
    vf = initialize(vf, data)
    vf = covariate_assign(vf, [2, 4, 6, 8, 10, 12])
    vf = covariate_assign(vf, np.arange(1, 7) * 1.5 - 0.5)
    return np.asarray(getCovariate(vf), dtype=np.float64)


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
