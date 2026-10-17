import statistics
import time
from assertthat import has_attr
from assertthat.objects import Vector
x = Vector([1, 2, 3], "integer")
named = Vector([1, 2, 3], "integer")
named.names = ["a", "b", "c"]

def one():
    return [has_attr(x, "names"), has_attr(named, "names"), has_attr(named, "something else"), has_attr(has_attr, "fail"), has_attr(10, "a")]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
