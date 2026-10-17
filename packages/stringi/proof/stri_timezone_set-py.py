import json
import statistics
import time
from pathlib import Path

from stringi.datetime import stri_timezone_get, stri_timezone_set

previous = stri_timezone_set("Pacific/Auckland")
stri_timezone_set(previous)
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_timezone_set-python.txt"
).write_text(f'stri_timezone_set("Pacific/Auckland") returns {previous}.\n')


def one():
    saved = stri_timezone_get()
    try:
        returned = stri_timezone_set("Pacific/Auckland")
        mid = stri_timezone_get()
        stri_timezone_set(saved)
        after = stri_timezone_get()
        return [returned, mid, after]
    finally:
        stri_timezone_set(saved)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
