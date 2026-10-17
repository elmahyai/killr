import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringr.length import str_width

x = str_width(["\u6c49\u5b57", "\U0001f60a"])
u = str_width(["\u00fc", "u\u0308"])
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_width-python.txt").write_text(
    "str_width of hanzi and an emoji returns " + ", ".join(str(item) for item in x) + ".\n"
    + "str_width of u-umlaut and u plus accent returns " + ", ".join(str(item) for item in u) + ".\n"
)

base = ["abc", NA, "", "NA", "\u00fc", "u\u0308", "\u6c49\u5b57", "\U0001f60a", "\u0105", "\u200b", "\u00ad"]


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
        "main": str_width(base * 40),
        "han": str_width(["\u6c49\u5b57", "\U0001f60a"]),
        "umlaut": str_width(["\u00fc", "u\u0308"]),
        "empty": str_width([]),
        "null": str_width(None),
        "na": str_width(NA),
        "named": str_width(Named(["ab", NA], ["a", "b"])),
        "logical": str_width([True, False]),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
