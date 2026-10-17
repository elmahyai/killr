import statistics
import time

from rlang import RLangError
from rlang.check_data_frame import _MISSING, check_data_frame


class _RDataFrame:
    klass = ("data.frame",)


def checker(foo=_MISSING, f=check_data_frame, **kwargs):
    return f(foo, **kwargs)


def one():
    empty = _RDataFrame()
    ok = "TRUE" if check_data_frame(empty) is None else "FALSE"
    try:
        checker(f=check_data_frame)
        msg1 = ""
    except RLangError as exc:
        msg1 = str(exc)
    try:
        checker(None, check_data_frame)
        msg2 = ""
    except RLangError as exc:
        msg2 = str(exc)
    try:
        checker([_RDataFrame(), _RDataFrame()], check_data_frame, allow_null=True)
        msg3 = ""
    except RLangError as exc:
        msg3 = str(exc)
    return "|".join([ok, msg1, msg2, msg3])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
