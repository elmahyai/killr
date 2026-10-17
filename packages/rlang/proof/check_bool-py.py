import statistics
import time

from rlang.check_bool import check_bool
from rlang import RLangError
from rlang.na_or import NA


def one():
    n = 1
    try:
        check_bool(n)
        err = ""
    except RLangError as exc:
        err = str(exc)
    parts = [
        "TRUE" if check_bool(True) is None else "FALSE",
        "TRUE" if check_bool(False) is None else "FALSE",
        "TRUE" if check_bool(NA, allow_na=True) is None else "FALSE",
        "TRUE" if check_bool(None, allow_null=True) is None else "FALSE",
        err,
    ]
    return "|".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
