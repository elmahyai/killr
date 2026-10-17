import statistics
import time

import numpy as np

from ordinal import clm2_control


def one():
    c = clm2_control()
    return np.array([
        ["ucminf", "Newton", "nlminb", "optim", "model.frame"].index(c["method"]) + 1,
        c["convTol"], c["ctrl"]["trace"], c["ctrl"]["grtol"],
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
