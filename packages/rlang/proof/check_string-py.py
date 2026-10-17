import statistics
import time

from rlang import RLangError
from rlang.check_string import check_string
from rlang.na_or import Character, NA


def one():
    n = 1
    empty = ""
    try:
        check_string(n)
        msg = ""
    except RLangError as exc:
        msg = str(exc)
    try:
        check_string(empty, allow_empty=False)
        empty_msg = "NOERR"
    except RLangError as exc:
        empty_msg = str(exc)
    parts = [
        "TRUE" if check_string("hello") is None else "FALSE",
        "TRUE" if check_string("") is None else "FALSE",
        "TRUE" if check_string(Character([NA]), allow_na=True) is None else "FALSE",
        "TRUE" if check_string(None, allow_null=True) is None else "FALSE",
        "TRUE" if check_string(["a"]) is None else "FALSE",
        empty_msg,
        msg,
    ]
    return "|".join(parts)


value = one()
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
