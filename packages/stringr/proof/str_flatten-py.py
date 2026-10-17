import json
import statistics
import string
import time
from pathlib import Path

from stringi._na import NA
from stringr.join import str_flatten

letters = list(string.ascii_lowercase)
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_flatten-python.txt").write_text(
    "str_flatten(letters[1:3], \", \", \" and \") returns "
    + str_flatten(letters[:3], ", ", " and ")[0]
    + ".\n"
    + "str_flatten(letters[1:2], \", \", \", and \") returns "
    + str_flatten(letters[:2], ", ", ", and ")[0]
    + ".\n"
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
        "main": str_flatten(letters * 4, "-"),
        "last": str_flatten(letters[:3], ", ", " and "),
        "oxford": str_flatten(letters[:2], ", ", ", and "),
        "na": str_flatten(["a", NA, "b"]),
        "na_rm": str_flatten(["a", NA, "b"], na_rm=True),
        "last_na": str_flatten(["a", NA], ", ", " and "),
        "empty": str_flatten([]),
        "null": str_flatten(None),
        "na_only": str_flatten(NA),
        "all_na_rm": str_flatten([NA, NA], na_rm=True),
        "last_empty": str_flatten(["a", "b"], "-", ""),
        "numbers": str_flatten([1, 2, 3], "-", " and "),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
