import statistics
import time

import numpy as np

from ordinal import clm_control


def one():
    c = clm_control()
    return np.array([
        ["Newton", "model.frame", "design", "ucminf", "nlminb", "optim"].index(c["method"]) + 1,
        ["negative", "positive"].index(c["sign.location"]) + 1,
        ["positive", "negative"].index(c["sign.nominal"]) + 1,
        ["warn", "silent", "stop", "message"].index(c["convergence"]) + 1,
        c["trace"], c["maxIter"], c["gradTol"], c["relTol"], c["tol"],
        c["maxLineIter"], c["maxModIter"],
    ], dtype=float)

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
