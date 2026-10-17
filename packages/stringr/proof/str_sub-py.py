import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringr.sub import str_sub

hw = "Hadley Wickham"
vec = str_sub(hw, [1, 8], [6, 14])
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_sub-python.txt").write_text(
    "str_sub(hw, 1, 6) returns " + str_sub(hw, 1, 6)[0] + ".\n"
    + "str_sub(hw, -7) returns " + str_sub(hw, -7)[0] + ".\n"
    + "str_sub(hw, c(1, 8), c(6, 14)) returns " + ", ".join(vec) + ".\n"
)

block = ["Hadley Wickham", "abcde", NA, ""] * 30


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
        "main": str_sub(block, 1, 4),
        "head": str_sub(hw, 1, 6),
        "end_only": str_sub(hw, end=6),
        "tail": str_sub(hw, -7),
        "vec": str_sub(hw, [1, 8], [6, 14]),
        "two": str_sub(["abcde", "ghifgh"], [1, 2], [2, 4]),
        "matrix": str_sub(hw, [[2, 5], [6, 7]]),
        "length_matrix": str_sub("abcdef", {"start": [1, 2], "length": [3, 2]}),
        "empty": str_sub([], 1, 2),
        "na_string": str_sub(["abc", NA], 1, 2),
        "na_index": str_sub("abc", NA, 2),
        "past": str_sub("abc", 10, 12),
        "before": str_sub("abc", 3, 1),
        "zero": str_sub("abc", 0, 2),
        "named": str_sub(Named(["abcdef", "ghijkl"], ["a", "b"]), 1, 2),
        "named_recycled": str_sub(Named(["abcdef"], ["a"]), [1, 2], [2, 3]),
        "null": str_sub(None),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
