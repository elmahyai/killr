import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_create, stri_datetime_fields

instant = stri_datetime_create(2015, 12, 31, 23, 59, 59, tz="UTC")
shown = stri_datetime_fields(instant, tz="UTC", locale="en_US")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_fields-python.txt"
).write_text(
    "stri_datetime_fields of 2015-12-31 23:59:59 UTC has Year "
    f"{shown['Year']} and Month {shown['Month']}.\n"
)


def plain(value):
    if value is NA:
        return None
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    hebrew = stri_datetime_create(5775, 8, 1, locale="@calendar=hebrew", tz="UTC")
    return {
        "utc": stri_datetime_fields([instant, NA], tz="UTC", locale="en_US"),
        "he": stri_datetime_fields(hebrew, tz="UTC", locale="@calendar=hebrew"),
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
