import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_add_assign, stri_datetime_create

example = stri_datetime_add_assign(
    stri_datetime_create(2015, 1, 31, tz="UTC"),
    units="months",
    tz="UTC",
    value=1,
)
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_add<--python.txt"
).write_text(
    f"stri_datetime_add<- of 2015-01-31 plus one month returns {example:.0f}.\n"
)


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    base = stri_datetime_create(2015, 1, 31, tz="UTC")
    epoch = stri_datetime_create(2015, 1, 1, tz="UTC")
    return [
        stri_datetime_add_assign(base, units="months", tz="UTC", value=1),
        *stri_datetime_add_assign(
            [epoch, epoch], units="hours", tz="UTC", value=[1, NA]
        ),
        stri_datetime_add_assign(
            epoch, units="years", tz="UTC", locale="@calendar=hebrew", value=1
        ),
    ]


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
