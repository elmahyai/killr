import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringr.length import str_length

x = str_length(["i", "like", "programming", NA])
u = str_length(["\u00fc", "u\u0308"])
shown = ", ".join("NA" if item is NA else str(item) for item in x)
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_length-python.txt").write_text(
    "str_length([\"i\", \"like\", \"programming\", NA]) returns "
    + shown
    + ".\n"
    + "str_length of u-umlaut and u plus accent returns "
    + ", ".join(str(item) for item in u)
    + ".\n"
)

base = ["abc", NA, "", "NA", "\u00fc", "u\u0308", "\u6c49\u5b57", "\U0001f60a", "\u0105"]


def plain(value):
    if value is NA:
        return None
    if isinstance(value, Named):
        return {"data": [plain(item) for item in value], "names": list(value.names)}
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    return {
        "main": str_length(base * 40),
        "scalar": str_length("abc"),
        "na": str_length(NA),
        "empty": str_length([]),
        "null": str_length(None),
        "named": str_length(Named(["ab", NA], ["a", "b"])),
        "numbers": str_length([1, 1.5, NA]),
        "logical": str_length([True, False, NA]),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
