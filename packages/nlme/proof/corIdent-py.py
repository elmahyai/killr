import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corident import coef, corIdent


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        cs1 = corIdent(form="~ 1 | Subject")
    return np.concatenate(
        [
            np.asarray(cs1.value, dtype=np.float64),
            np.asarray(coef(cs1, unconstrained=True).values, dtype=np.float64),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
parts = ",".join("%.17g" % float(part) for part in value)
print('{"value":[%s],"median_ms":%.17g}' % (parts, statistics.median(elapsed)))
