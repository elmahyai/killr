import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_add, stri_datetime_create

example = stri_datetime_add(
    stri_datetime_create(2024, 1, 31, tz="UTC"), 1, units="months", tz="UTC"
)
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_add-python.txt"
).write_text(f"stri_datetime_add of 2024-01-31 plus one month returns {example:.0f}.\n")


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    jan2015 = stri_datetime_create(2015, 1, 31, tz="UTC")
    jan2024 = stri_datetime_create(2024, 1, 31, tz="UTC")
    spring = stri_datetime_create(2015, 3, 28, 12, tz="Europe/Brussels")
    start = stri_datetime_create(2025, 4, 20, tz="UTC")
    epoch = stri_datetime_create(2015, 1, 1, tz="UTC")
    return [
        stri_datetime_add(jan2024, 1, "months", tz="UTC"),
        stri_datetime_add(jan2015, 1, units="mo", tz="UTC"),
        stri_datetime_add(start, 1, "years", tz="UTC", locale="@calendar=hebrew"),
        stri_datetime_add(start, 1, "years", tz="UTC"),
        stri_datetime_add(spring, 1, "days", tz="Europe/Brussels"),
        stri_datetime_add(spring, 24, "hours", tz="Europe/Brussels"),
        *stri_datetime_add(epoch, [1, NA], "days", tz="UTC"),
        *stri_datetime_add([epoch, NA], 1, "days", tz="UTC"),
        stri_datetime_add("2015-01-01", 0, "seconds"),
        stri_datetime_add(epoch, 1500, "milliseconds", tz="UTC"),
        stri_datetime_add(epoch, 1.9, "days", tz="UTC"),
    ]


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
