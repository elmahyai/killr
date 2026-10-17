import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.count import str_count
from stringr.pattern import boundary, coll, fixed

def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

fruit = ["apple", "banana", "pear", "pineapple"]
assert str_count(fruit, "a") == [1, 3, 1, 1]
sentence = 'str_count(c("apple", "banana", "pear", "pineapple"), "a") returns 1, 3, 1, 1.'

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_count-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "a\U0001F600b", "X.", "stra\u00dfe", "a\nb"]
    texts = base * 20
    return [
        str_count(texts, "a"),
        str_count(texts, fixed(".")),
        str_count(["a b c", "Hello. World!"], boundary("word")),
        str_count(["a b c", ""], ""),
        str_count("\u0131", coll("I", ignore_case=True, locale="tr")),
    ]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
