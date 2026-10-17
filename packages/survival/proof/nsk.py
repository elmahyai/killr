import statistics
import time

import numpy as np

from survival.nsk import nsk


def _fmt(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "NA"
    return f"{float(value):.17g}"


def one():
    x = [50.0, 60.0, 70.0, np.nan, 80.0, 55.0, 65.0, 40.0, 95.0]
    b1 = nsk(x, df=4, intercept=True)
    b2 = nsk(x, df=3)
    b3 = nsk(x, knots=[55, 70], intercept=False, boundary_knots=[40, 90])
    out = []
    out.extend(_fmt(v) for v in np.asarray(b1.data, dtype=float).reshape(-1, order="F"))
    out.extend(_fmt(v) for v in np.asarray(b2.data, dtype=float).reshape(-1, order="F"))
    out.extend(_fmt(v) for v in np.asarray(b3.data, dtype=float).reshape(-1, order="F"))
    out.extend(_fmt(v) for v in np.asarray(b1.knots, dtype=float).reshape(-1))
    out.extend(_fmt(v) for v in np.asarray(b1.boundary_knots, dtype=float).reshape(-1))
    out.extend(_fmt(v) for v in np.asarray(b3.knots, dtype=float).reshape(-1))
    out.extend(_fmt(v) for v in np.asarray(b3.boundary_knots, dtype=float).reshape(-1))
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
