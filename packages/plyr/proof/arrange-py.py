import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plyr.arrange import arrange

n = 200000
a = [(i * 17) % 23 for i in range(1, n + 1)]
b = [((i * 13) % 97) / 10 for i in range(1, n + 1)]
c = [(i % 11) + (i % 5) / 2 for i in range(1, n + 1)]
for i in range(10, n + 1, 1000):
    a[i - 1] = None
for i in range(20, n + 1, 1500):
    b[i - 1] = None
for i in range(30, n + 1, 2500):
    b[i - 1] = float("nan")
for i in range(40, n + 1, 4000):
    c[i - 1] = float("inf")
for i in range(50, n + 1, 4000):
    c[i - 1] = float("-inf")
for index, value in enumerate(b):
    if value == 0:
        b[index] = -0.0
frame = {"a": a, "b": b, "c": c}


def one():
    return arrange(frame, "a", "b", "c")


def show_a(value):
    return "NA" if value is None else str(int(value))


def show_d(value):
    if value is None:
        return "NA"
    number = float(value)
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return number.hex()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print("A " + " ".join(show_a(item) for item in value.columns["a"]))
print("B " + " ".join(show_d(item) for item in value.columns["b"]))
print("C " + " ".join(show_d(item) for item in value.columns["c"]))
print(f"MS {statistics.median(elapsed):.17g}")
