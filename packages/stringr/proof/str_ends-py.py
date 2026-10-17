import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.detect import str_ends
from stringr.pattern import fixed, regex

def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

fruit = ["apple", "banana", "pear", "pineapple"]
assert str_ends(fruit, "e") == [True, False, False, True]
sentence = 'str_ends(c("apple", "banana", "pear", "pineapple"), "e") returns TRUE, FALSE, FALSE, TRUE.'

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_ends-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

def one():
    base = ["apple", "banana", "pear", "pineapple", NA, "", "a\U0001F600b", "X.", "stra\u00dfe", "a\nb"]
    texts = base * 20
    return [
        str_ends(texts, "e|r"),
        str_ends(texts, fixed("e")),
        str_ends(["ab", "ba", "bc"], "a|b"),
        str_ends(["ab", "NA"], regex(NA)),
    ]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
