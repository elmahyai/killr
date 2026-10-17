import json
import statistics
import string
import time
from pathlib import Path

from stringi._na import NA
from stringr.join import str_c

letters = list(string.ascii_lowercase)
upper = list(string.ascii_uppercase)
joined = str_c("Letter", letters[:3], sep=": ")
missing = str_c(["a", NA, "b"], "-d")
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_c-python.txt").write_text(
    "str_c(\"Letter\", letters[1:3], sep = \": \") returns " + ", ".join(joined) + ".\n"
    + "str_c(c(\"a\", NA, \"b\"), \"-d\") returns "
    + ", ".join("NA" if item is NA else item for item in missing)
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
        "main": str_c(letters * 5, upper * 5, sep="-"),
        "nulls": str_c(None, "a", None, "b"),
        "empty": str_c(),
        "null_only": str_c(None),
        "char0": str_c("x", []),
        "na": str_c(["a", NA, "b"], "-d"),
        "collapse": str_c(letters[:3], collapse=", "),
        "sep": str_c("Letter", letters[:2], sep=": "),
        "one": str_c(["a", "b"]),
        "numbers": str_c([1, 2], ["x", "y"]),
        "collapse_empty": str_c(["a", "b"], collapse=""),
        "collapse_of_empty": str_c([], collapse=","),
        "collapse_only": str_c(collapse=","),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
