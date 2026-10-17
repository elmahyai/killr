import statistics
import time

from rlang import env
from rlang.as_string import Symbol
from rlang.duplicate import duplicate
from rlang.na_or import Integer
from rlang.obj_address import obj_address


def one():
    x = [Integer([1, 2, 3]), Integer([4, 5, 6])]
    d = duplicate(x)
    ds = duplicate(x, shallow=True)
    e = env(a=1)
    foo = Symbol("foo")
    return ",".join(
        "TRUE" if item else "FALSE"
        for item in (
            d[0].values == x[0].values and d[1].values == x[1].values,
            obj_address(d) != obj_address(x),
            obj_address(d[0]) != obj_address(x[0]),
            obj_address(ds[0]) == obj_address(x[0]),
            obj_address(ds) != obj_address(x),
            duplicate(e) is e,
            duplicate(foo) is foo,
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
