import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.regex import stri_match


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


assert stri_match("ab12", regex="([0-9]+)") == [["12", "12"]]
sentence = 'stri_match("ab12", regex = "([0-9]+)") returns 12, 12.'


def one():
    base = ["The 12 foxes and 7 dogs ran.", "no digits here", "99", NA, "", "a😀b12"]
    texts = base * 70
    return stri_match(texts, r"(\d+)", mode="last")


OUT = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_match-python.txt')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
