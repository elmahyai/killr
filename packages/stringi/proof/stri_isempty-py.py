import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.length import stri_isempty

example = stri_isempty(["", NA, "a"])
shown = ", ".join("NA" if value is NA else ("TRUE" if value else "FALSE") for value in example)
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_isempty-python.txt").write_text(
    f"stri_isempty([\"\", NA, \"a\"]) returns {shown}.\n"
)

base = [
    "abc",
    NA,
    "",
    "NA",
    "\u0105",
    "\U0001F606",
    "\uFF21",
    "A\u0301",
    "\U0001F1FA\U0001F1F8",
    "\U0001F468\u200D\U0001F469\u200D\U0001F467",
    "\u1161\u11A8",
    "\u00AD",
    "\u200B",
    "\u1100",
    "\u200D\u2640",
    "\u0301",
    "\U0001F1E6\U0001F1E7\U0001F1E8",
    "\u2600",
    chr(0x1FAE9),
    chr(0x1171E),
    "\u200D" + chr(0x1FAE9),
    chr(0x1F8B2),
]


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    return {
        "main": stri_isempty(base * 80),
        "ints": stri_isempty([1, 2, 3]),
        "logical": stri_isempty([True, False, NA]),
        "int_big": stri_isempty([10000000]),
        "doubles": stri_isempty([1.5, 1e-4, 1e5, float("inf"), float("-inf"), float("nan"), 1 / 3, 2**-1074]),
        "complex": stri_isempty([1 + 2j]),
        "mixed": stri_isempty(["a", 1, True, NA, 1.5]),
        "promoted": stri_isempty([10000000, 1.0]),
        "int_bool": stri_isempty([1, True]),
        "empty": stri_isempty(None),
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
