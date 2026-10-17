import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr2")
from httr2.example_url import example_url
from rlang import RLangError


def one():
    try:
        return example_url()
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
