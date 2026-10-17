import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringr.escape import str_conv

raw = bytes([177])
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_conv-python.txt").write_text(
    "str_conv(x, \"ISO-8859-2\") returns " + str_conv(raw, "ISO-8859-2")[0] + ".\n"
    + "str_conv(x, \"ISO-8859-1\") returns " + str_conv(raw, "ISO-8859-1")[0] + ".\n"
)


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
    raw = bytes([177])
    return {
        "main": str_conv([raw] * 40, "ISO-8859-2"),
        "latin2": str_conv(raw, "ISO-8859-2"),
        "latin1": str_conv(raw, "ISO-8859-1"),
        "utf8": str_conv("a", "UTF-8"),
        "letter": str_conv("\u0105", "UTF-8"),
        "null": str_conv(None, "UTF-8"),
        "empty": str_conv([], "UTF-8"),
        "na": str_conv(NA, "UTF-8"),
        "two": str_conv([raw, raw], "ISO-8859-1"),
        "named": str_conv(Named([raw], ["p"]), "ISO-8859-2"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
