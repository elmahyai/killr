import statistics
import time

import numpy as np

from ordinal import clmm_control


def one():
    c = clmm_control()
    return np.array([
        ["nlminb", "ucminf", "model.frame"].index(c["method"]) + 1,
        float(c["useMatrix"]),
        c["ctrl"]["trace"], c["ctrl"]["maxIter"], c["ctrl"]["gradTol"], c["ctrl"]["maxLineIter"],
        ["warnOnly", "noWarn", "giveError"].index(c["ctrl"]["innerCtrl"]) + 1,
        c["optCtrl"]["trace"],
        ["warn", "error", "message"].index(c["checkRanef"]) + 1,
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
