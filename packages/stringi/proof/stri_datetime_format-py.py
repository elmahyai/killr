import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_create, stri_datetime_format

instant = stri_datetime_create(2015, 12, 31, 23, 59, 59, tz="UTC")
shown = stri_datetime_format(instant, "uuuu-MM-dd HH:mm:ss", tz="UTC")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_format-python.txt"
).write_text(f"stri_datetime_format of 2015-12-31 23:59:59 UTC is {shown}.\n")


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    return [
        stri_datetime_format(instant, "uuuu-MM-dd HH:mm:ss", tz="UTC"),
        stri_datetime_format(instant, "date_full", tz="UTC", locale="en_US"),
        stri_datetime_format(instant, "time_full", tz="UTC", locale="en_US"),
        stri_datetime_format(instant, "time_relative_full", tz="UTC", locale="en_US"),
        stri_datetime_format(instant, "datetime_relative_medium", tz="UTC", locale="en_US"),
        stri_datetime_format(instant, "date_short", tz="UTC", locale="C"),
        stri_datetime_format(instant, "date_short", tz="UTC", locale="  en_US  "),
        stri_datetime_format(
            instant, "yyyy.MM.dd 'at' HH:mm:ss zzz", tz="Europe/Warsaw", locale="pl_PL"
        ),
        *stri_datetime_format([instant, NA], ["uuuu", NA], tz="UTC"),
        stri_datetime_format("2015-01-01", "uuuu-MM-dd HH:mm:ss", tz="UTC"),
    ]


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
