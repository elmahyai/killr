import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.sub import str_sub_assign


def chain(text):
    text = str_sub_assign(text, 1, 1, "A")
    text = str_sub_assign(text, -1, -1, "K")
    text = str_sub_assign(text, -2, -2, "GHIJ")
    return str_sub_assign(text, 2, -2, "")


Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_sub<--python.txt").write_text(
    "str_sub<- on BBCDEF returns " + chain("BBCDEF")[0] + ".\n"
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
    block = ["BBCDEF", "abcdef"] * 40
    return {
        "main": str_sub_assign(block, 1, 1, "Q"),
        "chain": chain("BBCDEF"),
        "omit": str_sub_assign(["abcd", NA], 1, 1, "Z", omit_na=True),
        "no_omit": str_sub_assign(["abcd", NA], 1, 1, "Z"),
        "recycle": str_sub_assign(["abcd", "efgh"], 1, 1, "Z"),
        "matrix": str_sub_assign(["abcdef", "ghijkl"], [[1, 2], [2, 3]], value=["X", "YZ"]),
        "omit_index": str_sub_assign("abcdef", NA, 2, "Z", omit_na=True),
        "drop_index": str_sub_assign("abcdef", NA, 2, "Z"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
