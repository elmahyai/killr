import statistics
import time

from rlang.as_string import Symbol
from rlang.is_symbol import is_symbol


def one():
    foo = Symbol("foo")
    return ",".join(
        "TRUE" if item else "FALSE"
        for item in (
            is_symbol(foo),
            is_symbol(1),
            is_symbol(foo, "foo"),
            is_symbol(foo, ("bar", "foo")),
            is_symbol(foo, "bar"),
        )
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
