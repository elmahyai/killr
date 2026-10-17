import statistics
import time

import numpy as np

from survival.surv2 import FactorEvent, Surv2


def _matrix_token(value):
    if isinstance(value, float) and np.isnan(value):
        return "NA"
    text = f"{float(value):.17g}"
    return text


def _repeated_token(repeated):
    if repeated is True:
        return "TRUE"
    if repeated is False:
        return "FALSE"
    return str(repeated)


def serialize_surv2(x):
    states = x.states
    flat = x.matrix().reshape(-1, order="F")
    return [
        "|".join(x.character()),
        "|".join(_matrix_token(value) for value in flat),
        "|".join(states) if states else "",
        x.clabel or "",
        _repeated_token(x.repeated),
    ]


def one():
    a = Surv2([1, 2.5, 10, float("nan")], [1, 0, 1, 1])
    b = Surv2([1, 2, 3], [True, False, True])
    c = Surv2([10, 20, 30], [1, 2, 1])
    d = Surv2(
        [70, 72, 75, 78, 80, 82, 85],
        FactorEvent(
            ["CU", "CU", "MCI", "CU", "MCI", "MCI", "dementia"],
            ["CU", "MCI", "dementia"],
        ),
        repeated="first",
    )
    out = []
    for item in (a, b, c, d):
        out.extend(serialize_surv2(item))
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
