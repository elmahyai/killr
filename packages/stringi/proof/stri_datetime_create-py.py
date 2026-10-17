import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_create

example = stri_datetime_create(2015, 1, 1, tz="UTC")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_create-python.txt"
).write_text(
    f'stri_datetime_create(2015, 1, 1, tz = "UTC") returns {example:.0f}.\n'
)


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return [
            stri_datetime_create(2015, 1, 1, tz="UTC"),
            stri_datetime_create(2015, 12, 31, 23, 59, 59.999, tz="UTC"),
            stri_datetime_create(2015, 2, 29, tz="UTC"),
            stri_datetime_create(2015, 2, 29, lenient=True, tz="UTC"),
            stri_datetime_create(5775, 8, 1, locale="@calendar=hebrew", tz="UTC"),
            stri_datetime_create(2015, 1, 1, 0, 0, 0.0015, tz="UTC"),
            stri_datetime_create(2015, 1, 1, 0, 0, 1.9995, tz="UTC"),
            stri_datetime_create(2015, 1, 1, 0, 0, 59.9995, tz="UTC"),
            *stri_datetime_create([2015, NA], 1, 1, tz="UTC"),
            stri_datetime_create(1e10, 1, 1, tz="UTC"),
            *stri_datetime_create([2015, 2016], 1, [1, 2, 3], tz="UTC"),
            stri_datetime_create(2015, 1, 1.9, tz="UTC"),
        ]


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
