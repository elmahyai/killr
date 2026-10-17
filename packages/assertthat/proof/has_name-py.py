import statistics
import time
from assertthat import has_name
from assertthat.objects import NA, Vector
x = Vector([1, 2, 3], "integer")
named = Vector([1, 2, 3], "integer")
named.names = ["a", "b", "c"]

def one():
    return [has_name(x, "a"), has_name(named, "b"), has_name(named, "something else"), has_name(named, NA), has_name(named, ["a", "b"]), has_name(named, ["a", "b", "c"]), has_name(named, ["a", "d"])]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
