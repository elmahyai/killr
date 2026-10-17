import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.locate import str_locate_all
from stringr.pattern import boundary, coll, fixed


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, dict):
        return {key: canon(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def show(groups):
    blocks = []
    for index, rows in enumerate(groups, start=1):
        lines = [f"[[{index}]]", "start end"]
        for row in rows:
            lines.append(" ".join("NA" if is_na(cell) else str(cell) for cell in row))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


fruit = ["apple", "banana", "pear", "pineapple"]
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_locate_all-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(show(str_locate_all(fruit, "a")) + "\n", encoding="utf-8")


def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "abab", "a\U0001f600b"]
    texts = base * 60
    return {
        "regex": str_locate_all(texts, "a"),
        "miss": str_locate_all(texts, "e"),
        "fixed": str_locate_all(["x.x.", "ab"] * 40, fixed(".")),
        "coll": str_locate_all(["\u0131I"] * 20, coll("I", ignore_case=True, locale="tr")),
        "bound": str_locate_all([" ab  cd", "a b"] * 30, boundary("word")),
        "empty": str_locate_all(["abc", "pear"] * 20, ""),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
