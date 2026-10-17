import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reshape2.dcast import dcast, mean

n = 20000
letters = [chr(ord("A") + k) for k in range(26)]
month = [(i % 12) + 1 for i in range(1, n + 1)]
variable = [letters[i % 5] for i in range(1, n + 1)]
value_column = [((i * 13) % 97) + (i % 7) / 10 for i in range(1, n + 1)]
frame = {"month": month, "variable": variable, "value": value_column}


def one():
    return dcast(frame, "month ~ variable", mean)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

names = [name for name, _column in value.columns]
print("NAMES " + " ".join(names))
print("MONTH " + " ".join(str(item) for item in value.columns[0][1].values))
for name, column in value.columns[1:]:
    print("COL " + name + " " + " ".join(format(item, ".17g") for item in column.values))
print(f"MS {statistics.median(elapsed):.17g}")
