import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.detect import str_detect
from stringr.pattern import coll, fixed

def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

fruit = ["apple", "banana", "pear", "pineapple"]
assert str_detect(fruit, "a") == [True, True, True, True]
sentence = 'str_detect(c("apple", "banana", "pear", "pineapple"), "a") returns TRUE, TRUE, TRUE, TRUE.'

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_detect-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "a\U0001F600b", "X.", "stra\u00dfe", "a\nb"]
    texts = base * 20
    return [
        str_detect(texts, "a"),
        str_detect(texts, fixed(".")),
        str_detect(["\u0131", "I", "i"], coll("I", ignore_case=True, locale="tr")),
    ]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
