import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.trunc import str_trunc


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


x = "This string is moderately long"
lines = [
    repr(str_trunc(x, 20, "right")),
    repr(str_trunc(x, 20, "left")),
    repr(str_trunc(x, 20, "center")),
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_trunc-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "right": str_trunc("This string is moderately long", 20, "right"),
        "left": str_trunc("This string is moderately long", 20, "left"),
        "center": str_trunc("This string is moderately long", 20, "center"),
        "c4": str_trunc("This string is moderately long", 4, "center"),
        "c5": str_trunc("This string is moderately long", 5, "center"),
        "c3": str_trunc("This string is moderately long", 3, "center"),
        "na": str_trunc(["foobar", NA], 5),
        "vec": str_trunc(["abcd", "abcde", "abcdef"], 5),
        "dots": str_trunc(["", "a", "aa", "aaa", "aaaa", "aaaaaaa"], 4, "center", ".."),
        "emoji": str_trunc("a\U0001f600bcdef", 5),
        "empty": str_trunc([], 4)
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
