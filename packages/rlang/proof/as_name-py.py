import statistics
import time

from rlang.as_label import Quosure
from rlang.as_name import as_name
from rlang.as_string import Symbol


def one():
    foo = Symbol("foo")
    bar = Symbol("bar")
    return "|".join(
        [
            as_name(foo),
            as_name(bar),
            as_name(Quosure(foo)),
            as_name("plain"),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
