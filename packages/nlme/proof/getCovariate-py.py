import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corar1 import corAR1
from nlme.corexp import corExp
from nlme.getcovariate import getCovariate
from nlme.getgroups import GroupedDataFrame
from nlme.var_power import initialize, varPower


def one():
    frame = GroupedDataFrame(
        columns={
            "y": np.asarray([1, 2, 3, 4, 5, 6], dtype=np.float64),
            "x": np.asarray([1.2, 2.5, 3.1, 4.0, 5.5, 6.3], dtype=np.float64),
            "g": np.asarray([1, 1, 2, 2, 2, 3], dtype=np.float64),
        },
        formula="y ~ x | g",
        group_levels=("a", "b", "c"),
    )
    c1 = getCovariate(frame, "~x")
    c2 = getCovariate(frame, "y ~ log(x) | g")
    c3 = getCovariate(frame, "y ~ 1 | g")
    vf = initialize(varPower(0.35, form="~x"), {"y": frame.columns["y"], "x": frame.columns["x"]})
    c4 = getCovariate(vf)
    c5 = getCovariate(corAR1(0.2, form="~ 1 | g"), data=frame)
    c6 = getCovariate(corAR1(0.2, form="~ x | g"), data=frame)
    c7 = getCovariate(corExp(0.5, form="~ x"), data=frame)
    c8 = getCovariate(corExp(0.5, form="~ x | g"), data=frame)
    parts = [c1, c2, c3, c4, *c5, *c6, c7, *c8]
    return np.concatenate([np.asarray(part, dtype=np.float64).reshape(-1) for part in parts])


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
