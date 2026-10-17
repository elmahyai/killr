import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.datetime import stri_timezone_info

shown = stri_timezone_info("Europe/London", locale="en_US")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_timezone_info-python.txt"
).write_text(
    'stri_timezone_info("Europe/London", locale = "en_US")$Name is '
    f"{shown['Name']}.\n"
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
    return {
        "london": stri_timezone_info(
            "Europe/London", locale="en_US", display_type="long"
        ),
        "utc": stri_timezone_info("UTC", locale="en_US", display_type="gmt_long"),
        "short": stri_timezone_info(
            "Europe/London", locale="en_US", display_type="short"
        ),
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
