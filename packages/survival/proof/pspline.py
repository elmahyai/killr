import statistics
import time

import numpy as np

from survival.pspline import pspline


def one():
    x = np.array([50.0, 60.0, 70.0, np.nan, 80.0, 55.0, 65.0, 40.0, 95.0])
    p = pspline(x, df=4, penalty=False)
    p2 = pspline(x, df=4)
    def _fmt(value):
        if np.isnan(value):
            return "NA"
        return f"{float(value):.17g}"

    out = [_fmt(value) for value in np.asarray(p.data, dtype=float).flatten(order="F")]
    out.extend(_fmt(value) for value in np.asarray(p2.pparm, dtype=float).flatten(order="F"))
    out.extend(p2.varname)
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
