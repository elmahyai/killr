import statistics
import time

from rlang.as_label import Quosure
from rlang.as_string import Symbol
from rlang.is_quosure import is_quosure


def one():
    q = Quosure(Symbol("my_quosure"))
    return ",".join(
        "TRUE" if item else "FALSE"
        for item in (
            is_quosure(q),
            is_quosure(1),
            is_quosure(None),
            is_quosure(Symbol("foo")),
            is_quosure(Quosure(Symbol("bar"))),
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
