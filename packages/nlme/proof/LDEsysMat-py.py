import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.lde_sys_mat import LDEsysMat


def one():
    incidence = {
        "Par": (1, 2, 3),
        "From": (1, 2, 2),
        "To": (2, 1, 0),
    }
    return LDEsysMat([1.2, 0.3, 0.4], incidence).reshape(-1, order="F")


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
