import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.smartbind import smartbind


def one():
    out = smartbind(
        {"x": [1, 2], "y": ["a", "b"]},
        {"y": ["c"], "z": [3]},
        fill=None,
    )
    return ["|".join("<NA>" if row[column] is None else str(row[column]) for column in out.columns)
            for row in out.to_dicts()]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
