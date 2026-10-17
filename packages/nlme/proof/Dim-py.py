import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corar1 import corAR1
from nlme.corexp import corExp
from nlme.dim import Dim
from nlme.pdmat import pdMat


def one():
    grp = [1, 1, 2, 2, 2, 3, 3, 3, 3]
    cs1 = corAR1(0.3, form="~ 1 | Subject")
    cs2 = corExp(0.5, form="~ x | Subject")
    d1 = Dim(cs1, groups=grp)
    d2 = Dim(cs2, groups=grp)
    return np.asarray(
        [
            *Dim(np.arange(1, 7).reshape(2, 3)),
            *Dim(pdMat(np.eye(3))),
            *Dim(pdMat(np.diag([1.0, 2.0, 3.0, 4.0]), pdClass="pdDiag")),
            d1.N,
            d1.M,
            d1.max_len,
            d1.sum_len_sq,
            *d1.len,
            *d1.start,
            d2["N"],
            d2["M"],
            d2["spClass"],
            d2["sumLenSq"],
            *d2["len"],
            *d2["start"],
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
