import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringi.sub import IndexMatrix
from stringr.sub import str_sub_all

pair = str_sub_all(["abcde", "ghifgh"], [1, 2], [2, 4])
shown = " | ".join(" ".join(item) for item in pair)
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_sub_all-python.txt").write_text(
    "str_sub_all(x, c(1, 2), c(2, 4)) returns " + shown + ".\n"
)

block = ["abcde", "ghifgh"] * 40


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
        "main": str_sub_all(block, [1, 2], [2, 4]),
        "pair": str_sub_all(["abcde", "ghifgh"], [1, 2], [2, 4]),
        "one": str_sub_all("abcdef", [1, 3], [2, 5]),
        "matrix": str_sub_all(
            ["abcde", "ghifgh"],
            IndexMatrix([[2, 5], [6, 7]], colnames=("start", "end")),
        ),
        "length_matrix": str_sub_all("abcdef", {"start": [1, 2], "length": [3, 2]}),
        "per_string": str_sub_all(["abcdef", "ghijkl"], [[1, 3], [2, 4]], -1),
        "names": str_sub_all(Named(["abcd", "efgh"], ["a", "b"]), 1, 2),
        "empty": str_sub_all([], [1, 2], [2, 3]),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
