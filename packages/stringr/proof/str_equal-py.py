import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.equal import str_equal

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
        "main": str_equal(long, list(reversed(long))),
        "accent": str_equal("\u00e1", "a\u0301"),
        "ohm": str_equal("\u2126", "\u03a9"),
        "case": str_equal("a", "A"),
        "ignore": str_equal(["a", "b", "A"], ["A", "b", "a"], ignore_case=True),
        "recycle": str_equal("a", ["a", "b", "A"]),
        "empty": str_equal("a", []),
        "na": str_equal(["a", NA], ["a", "a"]),
        "bom": str_equal("\ufeffa", "a"),
        "strength": str_equal("a", "A", strength=1),
        "override": str_equal("a", "A", ignore_case=True, strength=3),
        "numeric": str_equal("02", "2", numeric=True),
        "lexical": str_equal("02", "2"),
        "both_empty": str_equal([], []),
    }


out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output")
out.mkdir(parents=True, exist_ok=True)
(out / "str_equal-python.txt").write_text(
    'str_equal("\\u00e1", "a\\u0301") returns TRUE.\n',
    encoding="utf-8",
)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
