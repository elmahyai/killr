import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_count_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


result = stri_count_fixed("babab", "b")
sentence = f'stri_count_fixed("babab", "b") returns {result[0]}.'

def one():
    return stri_count_fixed(
        ["aaa"] * 2000 + ["abababa"] * 500 + ["", NA, "ÉÉÉ", "aAaA"],
        ["aa"] * 2000 + ["aba"] * 500 + ["z", "z", "éé", "aa"],
        case_insensitive=True,
        overlap=True,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_count_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
