import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.sort import str_order

base = [
    "apple", "car", "happy", "char",
    "100a10", "100a5", "2b", "2a",
    "a", "A", "b", "B",
    NA, "", "NA",
    "\ufeffabc", "abc",
    "cote", "côte", "coté", "côté",
    "motley", "mötley",
    "10", "2", "100",
]
long = base * 40


def plain(value):
    if value is NA or is_na(value):
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    return {
        "main": str_order(long),
        "cs": str_order(["apple", "car", "happy", "char"], locale="cs"),
        "num": str_order(["2", "1", "10"], numeric=True),
        "lex": str_order(["2", "1", "10"]),
        "dec": str_order(["a", "b", "a"], decreasing=True),
        "drop": str_order(["b", NA, "a"], na_last=NA),
        "first": str_order(["b", NA, "a"], na_last=False),
        "last": str_order(["b", NA, "a"], na_last=True),
        "bom": str_order(["\ufeffabc", "abc", "b", NA, "a"]),
        "ties": str_order(["b", "a", "b", "a"]),
        "empty": str_order([]),
    }


out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output")
out.mkdir(parents=True, exist_ok=True)
(out / "str_order-python.txt").write_text(
    'str_order(["apple", "car", "happy", "char"]) returns 1, 2, 4, 3.\n',
    encoding="utf-8",
)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
