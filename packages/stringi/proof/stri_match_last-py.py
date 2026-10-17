import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.regex import stri_match_last


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


assert stri_match_last("a1b2", "([0-9])") == [["2", "2"]]
sentence = 'stri_match_last("a1b2", regex = "([0-9])") returns 2, 2.'


def one():
    base = ["The 12 foxes and 7 dogs ran.", "no digits here", "99", NA, "", "a😀b12"]
    texts = base * 70
    return stri_match_last(texts, r"(\d+)")


OUT = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_match_last-python.txt')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
