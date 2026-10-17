import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_parse

example = stri_datetime_parse("2015-02-28", "yyyy-MM-dd", tz="UTC")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_parse-python.txt"
).write_text(
    'stri_datetime_parse("2015-02-28", "yyyy-MM-dd", tz = "UTC") returns '
    f"{example:.0f}.\n"
)


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    return [
        stri_datetime_parse("2015-02-28", "yyyy-MM-dd", tz="UTC"),
        stri_datetime_parse("2015-02-29", "yyyy-MM-dd", tz="UTC"),
        stri_datetime_parse("2015-02-29", "yyyy-MM-dd", lenient=True, tz="UTC"),
        stri_datetime_parse(
            "19 lipca 2015", "date_long", locale="pl_PL", tz="Europe/Warsaw"
        ),
        *stri_datetime_parse(["2015-01-01", NA], "yyyy-MM-dd", tz="UTC"),
        stri_datetime_parse("not a date", "yyyy-MM-dd", tz="UTC"),
    ]


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
