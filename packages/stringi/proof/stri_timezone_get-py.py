import json
import statistics
import time
from pathlib import Path

from stringi.datetime import stri_timezone_get

shown = stri_timezone_get()
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_timezone_get-python.txt"
).write_text(f"stri_timezone_get() returns {shown}.\n")


def one():
    return stri_timezone_get()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
