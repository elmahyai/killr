import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.sort import str_sort

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
        "main": str_sort(long),
        "cs": str_sort(["apple", "car", "happy", "char"], locale="cs"),
        "num": str_sort(["100a10", "100a5", "2b", "2a"], numeric=True),
        "lex": str_sort(["100a10", "100a5", "2b", "2a"]),
        "dec": str_sort(["a", "c", "b", NA], decreasing=True),
        "drop": str_sort(["b", NA, "a"], na_last=NA),
        "first": str_sort(["b", NA, "a"], na_last=False),
        "bom": str_sort(["\ufeffabc", "abc", "b", NA, "a"]),
        "nums": str_sort([10, 2, 1]),
        "doubles": str_sort([1e5, 2, 10, 1e-4]),
        "logicals": str_sort([True, False, True]),
        "french": str_sort(["cote", "coté", "côte", "côté"], french=True),
        "upper": str_sort(["a", "A", "b", "B"], uppercase_first=True),
        "plain": str_sort(["a", "A", "b", "B"]),
        "missing": str_sort(NA),
        "empty": str_sort([]),
    }


out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output")
out.mkdir(parents=True, exist_ok=True)
(out / "str_sort-python.txt").write_text(
    'str_sort(["100a10", "100a5", "2b", "2a"], numeric=True) returns 2a, 2b, 100a5, 100a10.\n',
    encoding="utf-8",
)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
