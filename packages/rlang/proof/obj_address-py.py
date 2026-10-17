import statistics
import time

from rlang import is_string
from rlang.as_label import MISSING
from rlang.na_or import Integer
from rlang.obj_address import obj_address


def one():
    x = Integer([1, 2, 3])

    def fn(x=MISSING):
        return obj_address(x)

    return ",".join(
        "TRUE" if item else "FALSE"
        for item in (
            obj_address(x) == obj_address(x),
            obj_address(x) != obj_address(Integer([1, 2, 3])),
            is_string(obj_address(MISSING)),
            fn() == obj_address(MISSING),
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
