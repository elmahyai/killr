import statistics
import time

from rlang.as_string import Symbol, as_string


def one():
    foo = Symbol("foo")
    bar = Symbol("bar")
    return "|".join([as_string(foo), as_string(bar), as_string("plain")])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
