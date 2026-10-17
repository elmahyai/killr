import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.detect import str_which
from stringr.pattern import fixed

def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

fruit = ["apple", "banana", "pear", "pineapple"]
assert str_which(fruit, "a") == [1, 2, 3, 4]
sentence = 'str_which(c("apple", "banana", "pear", "pineapple"), "a") returns 1, 2, 3, 4.'

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_which-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "a\U0001F600b", "X.", "stra\u00dfe", "a\nb"]
    texts = base * 20
    return [
        str_which(texts, "a"),
        str_which(texts, fixed(".")),
        str_which("apple", ["a", "x", "p"]),
        str_which(["a", NA, "b"], "."),
    ]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
