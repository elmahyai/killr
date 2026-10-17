import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.detect import str_like

def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

fruit = ["apple", "banana", "pear", "pineapple"]
assert str_like(fruit, "app%") == [True, False, False, False]
sentence = 'str_like(c("apple", "banana", "pear", "pineapple"), "app%") returns TRUE, FALSE, FALSE, FALSE.'

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_like-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "a\U0001F600b", "X.", "stra\u00dfe", "a\nb"]
    texts = base * 20
    return [
        str_like(texts, "a%"),
        str_like(texts, "%a%"),
        str_like(["ab%", "abX", "a_b", "100", "NA", NA], ["ab\\%", "ab_", "a\\_b", "100%", NA, "%"]),
    ]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
