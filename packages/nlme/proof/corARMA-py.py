import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corarma import coef, corARMA


def one():
    cs1 = corARMA([0.2, 0.3, -0.1], form="~ 1 | Mare", p=1, q=2)
    return np.asarray(
        [
            *cs1.value.tolist(),
            *coef(cs1, unconstrained=False).values.tolist(),
            *coef(cs1, unconstrained=True).values.tolist(),
        ],
        dtype=np.float64,
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
