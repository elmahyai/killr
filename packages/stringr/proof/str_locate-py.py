import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.locate import str_locate
from stringr.pattern import boundary, coll, fixed, regex


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, dict):
        return {key: canon(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def show(rows):
    lines = ["start end"]
    for row in rows:
        lines.append(" ".join("NA" if is_na(cell) else str(cell) for cell in row))
    return "\n".join(lines)


fruit = ["apple", "banana", "pear", "pineapple"]
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_locate-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(show(str_locate(fruit, "a")) + "\n", encoding="utf-8")


def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "a\U0001f600b", "The 12 foxes"]
    texts = base * 80
    return {
        "regex": str_locate(texts, "a"),
        "dollar": str_locate(texts, "$"),
        "vec": str_locate(["abc", "def", "pear"], ["a", "d", "e"]),
        "fixed": str_locate(["x.x", "ab", "a.b.c"] * 40, fixed(".")),
        "coll": str_locate(["\u0131", "I", "i"], coll("I", ignore_case=True, locale="tr")),
        "bound": str_locate([" xy", "ab", "a b c"] * 30, boundary("word")),
        "empty": str_locate(["abc", "x"] * 20, ""),
        "casefold": str_locate(["Cat", "dog"] * 20, regex("[a-z]+", ignore_case=True)),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
