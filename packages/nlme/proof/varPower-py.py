import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.var_ident import _NlmeFrame
from nlme.var_power import initialize, proof_values, varPower


def one():
    data = _NlmeFrame(
        {
            "y": np.arange(1, 7, dtype=np.float64),
            "x": np.array([1.2, 2.5, 3.1, 4.0, 5.5, 6.3], dtype=np.float64),
        }
    )
    vf = varPower(0.35, form="~x")
    vf = initialize(vf, data)
    return proof_values(vf)


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
