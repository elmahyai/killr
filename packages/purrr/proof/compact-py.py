import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from purrr.compact import NA, Double, Integer, List, Logical, compact


def build(n=4000):
    values = []
    names = []
    for i in range(1, n + 1):
        names.append(f"v{i}")
        if i % 5 == 0:
            values.append(None)
        elif i % 7 == 0:
            values.append(Double([]))
        elif i % 11 == 0:
            values.append(Double([NA]))
        elif i % 13 == 0:
            values.append(Double([float("nan")]))
        elif i % 17 == 0:
            values.append(Double([0.0, math.inf, -math.inf]))
        else:
            values.append(Double([i / 3, (i % 11) / 7]))
    return List(values, names)


def encode_num(value):
    if value is NA:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    return format(float(value), ".17g")


def encode_ex(ex):
    left = ex.values[0]
    right = ex.values[1]
    if isinstance(right, Logical) and right.values == [NA]:
        missing = "NA"
    else:
        missing = "BAD"
    return (
        f"a:character:{left.values[0]}|d:logical:{missing}"
        f"|n:{len(ex)}|names:{','.join(ex.names)}"
    )


def encode_big(value):
    parts = []
    for name, item in zip(value.names, value.values):
        bits = ",".join(encode_num(number) for number in item.values)
        parts.append(f"{name}:{bits}")
    return ";".join(parts)


x = build()


def one():
    ex = compact({"a": "a", "b": None, "c": Integer([]), "d": NA, "e": []})
    big = compact(x)
    return ex, big


example, big = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE EX " + encode_ex(example) + " BIG " + encode_big(big))
print(f"MS {statistics.median(elapsed):.17g}")
