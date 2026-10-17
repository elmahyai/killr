import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corcar1 import coef, corCAR1


def one():
    cs1 = corCAR1(0.2, form="~ 1 | Mare")
    return np.asarray(
        [
            cs1.value,
            float(coef(cs1, unconstrained=False).values[0]),
            float(coef(cs1, unconstrained=True).values[0]),
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
