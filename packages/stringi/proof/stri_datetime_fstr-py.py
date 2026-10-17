import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_datetime_fstr

shown = stri_datetime_fstr("%Y-%m-%d %H:%M:%S")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_fstr-python.txt"
).write_text(f'stri_datetime_fstr("%Y-%m-%d %H:%M:%S") returns {shown}.\n')


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
            *stri_datetime_fstr(
                [
                    "%Y-%m-%d %H:%M:%S",
                    "it's %Y",
                    "NA",
                    NA,
                    "%n",
                    "a'b",
                    "%Y%m",
                    "%c",
                    "datetime_full",
                ]
            ),
            *stri_datetime_fstr(
                ["datetime_full", "date_full"], ignore_special=False
            ),
            stri_datetime_fstr("date_full", ignore_special=1),
        ]


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
