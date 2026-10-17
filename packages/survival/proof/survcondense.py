import statistics
import time

from survival.fromtimeline import Categorical
from survival.surv_split import survSplit
from survival.surv_condense import survcondense


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
    aml = {
        "time": [
            9, 13, 13, 18, 23, 28, 31, 34, 45, 48, 161, 5, 5, 8, 8, 12, 16, 23, 27, 30, 33, 43, 45
        ],
        "status": [
            1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1
        ],
        "x": ["Maintained"] * 11 + ["Nonmaintained"] * 12,
    }
    n = len(aml["time"])
    aml = dict(aml, newid=list(range(1, n + 1)))
    test1 = survSplit("Surv(time, status) ~ .", aml, cut=[10, 20, 30], id="newid")
    test1_table = {name: col for name, col in zip(test1.names, test1.columns)}
    return _serialize(survcondense("Surv(tstart, time, status) ~ x", test1_table, id="newid"))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
