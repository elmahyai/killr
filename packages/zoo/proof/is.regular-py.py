import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.series import Zoo
from zoo.is_regular import is_regular


class _Ts:
    tsp = (2000.0, 2000.75, 4.0)


def one():
    idx = [2000 + 0.25 * i for i in range(10)]
    series = Zoo(np.arange(1, 11), idx)
    omit = Zoo(np.arange(1, 10), idx[:2] + idx[3:])
    gapped = Zoo(np.arange(1, 10), idx[:2] + idx[3:], frequency=4, regular=True)
    irregular = Zoo(np.arange(1, 5), [0, 1, 2.5, 4])
    flags = [
        is_regular(series), is_regular(series, True),
        is_regular(omit), is_regular(omit, True),
        is_regular(gapped), is_regular(gapped, True),
        is_regular(irregular), is_regular(irregular, True),
        is_regular(Zoo(np.array([1.0]), [1])),
        is_regular(Zoo(np.array([1.0]), [1], frequency=1, regular=True)),
        is_regular(Zoo(np.arange(1, 5), [1, 2, 4, 7])),
        is_regular(_Ts()),
        is_regular([1, 2, 4]),
    ]
    return [1.0 if flag else 0.0 for flag in flags]


def as_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], str):
            return "|".join(value)
        parts = []
        for item in value:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                parts.append("NA")
            else:
                parts.append(format(float(item), ".16g"))
        return "|".join(parts)
    array = np.asarray(value, dtype=float).reshape(-1)
    parts = []
    for number in array:
        number = float(number)
        parts.append("NA" if math.isnan(number) else format(number, ".16g"))
    return "|".join(parts)


value = as_text(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
