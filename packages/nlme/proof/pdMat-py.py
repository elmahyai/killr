import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.pdmat import fingerprint_pd_mat, pdMat


def one():
    matrix = np.diag(np.arange(1, 5, dtype=np.float64))
    pd1 = pdMat(matrix, pdClass="pdDiag")
    return fingerprint_pd_mat(pd1)


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
