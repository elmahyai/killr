import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.regex import stri_detect_regex


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


assert stri_detect_regex(["stringi R", "R STRINGI", "123"], "R.") == [False, True, False]
sentence = 'stri_detect_regex(c("stringi R", "R STRINGI", "123"), "R.") returns FALSE, TRUE, FALSE.'


def one():
    base = ["The 12 foxes and 7 dogs ran.", "no digits here", "99", NA, "", "a😀b12"]
    texts = base * 70
    return stri_detect_regex(texts, r"\d")


OUT = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_detect_regex-python.txt')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
