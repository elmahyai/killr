import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.dispatch import stri_subset


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

assert stri_subset(["stringi R", "123", ""], regex="^[0-9]+$") == ["123"]
sentence = "stri_subset([\"stringi R\", \"123\", \"\"], regex=\"^[0-9]+$\") returns 123."


def one():
    base = ["The 12 foxes and 7 dogs ran.", "no digits here", "99", NA, "", "a\U0001f600b12", "Lorem ipsum dolor sit amet"]
    texts = base * 60
    return stri_subset(texts, regex=r"\d")


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_subset-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
