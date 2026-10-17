import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.mixedsort import mixedsort


def fmt_one(z):
    if isinstance(z, str):
        return z
    if isinstance(z, (bool, np.bool_)):
        return "TRUE" if z else "FALSE"
    if z is None:
        return "NA"
    if isinstance(z, float) and np.isnan(z):
        return "NA"
    value = float(np.real(z))
    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return format(value, ".16g")


def flat(x):
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return "|".join(fmt_one(item) for item in x)
    array = np.asarray(x)
    return "|".join(fmt_one(v) for v in array.reshape(-1))


def one():
    treatment = [
        "Control", "Aspirin 10mg/day", "Aspirin 50mg/day",
        "Aspirin 100mg/day", "Acetomycin 100mg/day",
        "Acetomycin 1000mg/day",
    ]
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
    roman_lower = [
        "xix", "xii", "mcv", "iii", "iv", "dcclxxii", "cdxcii",
        "dcxcviii", "dcvi", "cci",
    ]
    parts = [
        flat(mixedsort(treatment)),
        flat(mixedsort(x)),
        flat(mixedsort(x, decreasing=True)),
        flat(mixedsort(x, na_last=False)),
        flat(mixedsort(x, blank_last=True)),
        flat(mixedsort([3, 1, 2])),
        flat(mixedsort(chapters, numeric_type="roman")),
        flat(mixedsort(roman_lower, numeric_type="roman", roman_case="lower")),
        flat(mixedsort(vals)),
        flat(mixedsort(vals, scientific=False)),
    ]
    return "|".join(parts)


mixedsort(["A", "B"])
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
