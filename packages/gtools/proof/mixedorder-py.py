import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.mixedorder import mixedorder


def flat(value):
    if value is None:
        return []
    return [float(x) for x in value.ravel(order="F")]


def one():
    x = list(reversed([
        "AA 0.50 ml", "AA 1.5 ml", "AA 500 ml", "AA 1500 ml",
        "EXP 1", "AA 1e3 ml", "A A A", "1 2 3 A", "NA", None, "1e2",
        "", "-", "1A", "1 A", "100", "100A", "Inf",
    ]))
    chapters = [
        "V. Non Sequiturs", "II. More Nonsense", "I. Nonsense",
        "IV. Nonesensical Citations", "III. Utter Nonsense",
    ]
    vals = ["3E1", "2E3", "4e0"]
    parts = [
        flat(mixedorder(x)),
        flat(mixedorder(x, decreasing=True)),
        flat(mixedorder(x, na_last=False)),
        flat(mixedorder(x, blank_last=True)),
        flat(mixedorder([3, 1, 2])),
        flat(mixedorder(chapters, numeric_type="roman")),
        flat(mixedorder(vals)),
        flat(mixedorder(vals, scientific=False)),
    ]
    return [item for part in parts for item in part]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
