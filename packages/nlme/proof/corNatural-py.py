import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.cornatural import coef, corNatural


def one():
    cs1 = corNatural([0.1, 0.2, 0.3], form="~ 1 | Subject")
    stored = np.asarray(cs1.value, dtype=np.float64)
    free = np.asarray(coef(cs1, unconstrained=True).values, dtype=np.float64)
    return np.concatenate([stored, free])


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
