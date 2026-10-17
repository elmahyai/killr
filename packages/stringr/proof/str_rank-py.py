import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.sort import str_rank

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
        "main": str_rank(long),
        "cs": str_rank(["apple", "car", "happy", "char"], locale="cs"),
        "num": str_rank(["2", "1", "10"], numeric=True),
        "lex": str_rank(["2", "1", "10"]),
        "ties": str_rank(["b", "a", "b", "a", NA]),
        "nums": str_rank([10, 2, 1]),
        "missing": str_rank([NA, "a", NA]),
        "empty": str_rank([]),
    }


out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output")
out.mkdir(parents=True, exist_ok=True)
(out / "str_rank-python.txt").write_text(
    'str_rank(["apple", "car", "happy", "char"]) returns 1, 2, 4, 3.\n',
    encoding="utf-8",
)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
