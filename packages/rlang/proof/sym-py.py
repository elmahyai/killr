import statistics
import time

from rlang import RLangError
from rlang.as_label import MISSING
from rlang.as_string import as_string
from rlang.sym import sym


def one():
    foo = sym("foo")
    try:
        sym(1.0)
        err = ""
    except RLangError as exc:
        err = str(exc)
    return "|".join(
        [
            as_string(sym("cyl")),
            "TRUE" if sym("") is MISSING else "FALSE",
            "TRUE" if sym(foo) is foo else "FALSE",
            err,
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
