import statistics
import time

from survival.fromtimeline import Categorical
from survival.surv_split import survSplit


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
    return lines


def one():
    tdata = {
        "id": [1, 2, 2, 2, 3, 3, 3, 4, 4],
        "time": [5, 3, 8, 11, 0, 5, 9, 2, 7],
        "state": Categorical(
            ["A", "A", "none", "B", "B", "none", "A", "A", "B"],
            ["none", "A", "B"],
        ),
        "x": list(range(1, 10)),
        "y": list(range(10, 1, -1)),
    }
    return _serialize(survSplit("Surv2(time, state) ~ .", tdata, id="id", cut=[2, 6, 9]))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
