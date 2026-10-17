import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringr.dup import str_dup

fruit = ["apple", "pear", "banana"]
lines = [
    "str_dup(fruit, 2) returns " + ", ".join(str_dup(fruit, 2)) + ".",
    "str_dup(fruit, 1:3) returns " + ", ".join(str_dup(fruit, [1, 2, 3])) + ".",
    "str_dup(c(\"a\", NA), 2, sep = \"-\") returns "
    + ", ".join("NA" if item is NA else item for item in str_dup(["a", NA], 2, sep="-"))
    + ".",
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_dup-python.txt").write_text(
    "\n".join(lines) + "\n"
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
    return {
        "main": str_dup(fruit * 40, 2),
        "sep": str_dup(fruit, 2, sep=" "),
        "times": str_dup(fruit, [1, 2, 3]),
        "na": str_dup(["a", NA], 2),
        "na_sep": str_dup(["a", NA], 2, sep="-"),
        "zero": str_dup(["a", NA], 0),
        "zero_sep": str_dup(["a", NA], 0, sep="-"),
        "negative": str_dup("a", -1),
        "na_times": str_dup("a", NA),
        "null_long": str_dup(None, [1, 2, 3]),
        "empty_one": str_dup([], 1),
        "string_null": str_dup("a", None),
        "float": str_dup("ab", 2.9),
        "float_sep": str_dup(["ab", "cd"], [1.2, 2.9], sep="-"),
        "logical": str_dup("ab", True),
        "names": str_dup(Named(["ab", "cd"], ["x", "y"]), 2),
        "names_recycle": str_dup(Named(["ab"], ["a"]), [1, 2, 3]),
        "both_null": str_dup(None, None),
        "both_empty": str_dup([], []),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
