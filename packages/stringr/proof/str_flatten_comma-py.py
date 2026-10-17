import json
import statistics
import string
import time
from pathlib import Path

from stringi._na import NA
from stringr.join import str_flatten_comma

letters = list(string.ascii_lowercase)
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_flatten_comma-python.txt").write_text(
    "str_flatten_comma(letters[1:3], \", and \") returns "
    + str_flatten_comma(letters[:3], ", and ")[0]
    + ".\n"
    + "str_flatten_comma(letters[1:2], \", and \") returns "
    + str_flatten_comma(letters[:2], ", and ")[0]
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
        "main": str_flatten_comma(letters[:4] * 30, ", and "),
        "three": str_flatten_comma(letters[:3], ", and "),
        "two": str_flatten_comma(letters[:2], ", and "),
        "one": str_flatten_comma("a", ", and "),
        "empty": str_flatten_comma([], ", and "),
        "na_pair": str_flatten_comma(["a", NA], ", and "),
        "na_rm": str_flatten_comma(["a", NA], ", and ", na_rm=True),
        "no_comma": str_flatten_comma(letters[:3], " and "),
        "comma_only": str_flatten_comma(letters[:2], ","),
        "or_last": str_flatten_comma(letters[:3], ", or "),
        "four": str_flatten_comma(letters[:4], ", and "),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
