import statistics
import time

import numpy as np

from survival.fromtimeline import Categorical
from survival.finegray import finegray


def _serialize(frame):
    lines = ["|".join(frame.names)]
    for name, col in zip(frame.names, frame.columns):
        if isinstance(col, Categorical):
            col = col.values
        if hasattr(col, "tolist"):
            col = col.tolist()
        tokens = []
        for value in col:
            if value is None or (isinstance(value, float) and value != value):
                tokens.append("NA")
            elif isinstance(value, float):
                tokens.append(f"{value:.17g}")
            else:
                tokens.append(str(value))
        lines.append(",".join(tokens))
    lines.append(frame.event)
    return lines


def one():
    labels = ["cen", "type1", "type2"]
    codes = [1, 2, 0, 1, 0, 0, 2, 1, 0, 0, 2, 0, 1, 0]
    fdata = {
        "time": [1, 2, 3, 4, 4, 4, 5, 5, 6, 8, 8, 9, 10, 12],
        "status": Categorical([labels[c] for c in codes], labels),
        "x": [5, 4, 3, 1, 2, 1, 1, 2, 2, 4, 6, 1, 2, 0],
        "id": list(range(1, 15)),
    }
    return _serialize(finegray("Surv(time, status) ~ .", fdata, count="fgcount"))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
