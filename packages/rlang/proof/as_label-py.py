import statistics
import time

from rlang.as_label import Call, Symbol, as_label
from rlang.na_or import Integer


def _fn():
    pass


def one():
    foo_bar = Call(Symbol("foo"), Symbol("bar"))
    foobar = Symbol("foobar")
    return "|".join(
        [
            as_label(foo_bar),
            as_label(foobar),
            as_label(Integer([1, 2, 3])),
            as_label(_fn),
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
