import statistics
import time

from rlang import RLangError
from rlang.colon_equals import colon_equals


def one():
    try:
        colon_equals(1, 2)
    except RLangError as exc:
        return str(exc)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
