import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.unique import str_unique

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
        "main": str_unique(long),
        "ignore": str_unique(["a", "b", "c", "B", "A"], ignore_case=True),
        "keep": str_unique(["a", "b", "c", "B", "A"]),
        "strength": str_unique(["motley", "mötley", "pinguino", "pingüino"], strength=1),
        "both": str_unique(["a", "A"], ignore_case=True, strength=3),
        "bom": str_unique(["\ufeffa", "a", "A", NA, NA]),
        "numeric": str_unique(["02", "2", "10", "10", "2"], numeric=True),
        "nums": str_unique([1, 1, 2]),
        "nas": str_unique([NA, NA]),
        "empty": str_unique([]),
    }


out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output")
out.mkdir(parents=True, exist_ok=True)
(out / "str_unique-python.txt").write_text(
    'str_unique(["a", "b", "c", "B", "A"], ignore_case=True) returns a, b, c.\n',
    encoding="utf-8",
)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
