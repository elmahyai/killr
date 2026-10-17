import json
import math
import statistics
import time
from pathlib import Path

from stringi.datetime import stri_datetime_fields, stri_datetime_now

sample = stri_datetime_now()
word = "TRUE" if math.isfinite(sample) else "FALSE"
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_now-python.txt"
).write_text(f"stri_datetime_now() returns one finite instant: {word}.\n")


def one():
    instant = stri_datetime_now()
    fields = stri_datetime_fields(instant, tz="UTC")
    return {
        "finite": math.isfinite(instant),
        "n_fields": len(fields),
        "names": list(fields),
        "types_int": all(isinstance(fields[name], int) for name in fields),
        "month_ok": 1 <= fields["Month"] <= 12,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
