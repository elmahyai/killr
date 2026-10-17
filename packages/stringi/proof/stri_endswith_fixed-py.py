import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_endswith_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


found = stri_endswith_fixed("ababa", "ba")
sentence = f'stri_endswith_fixed("ababa", "ba") returns {found[0]}.'

def one():
    return stri_endswith_fixed(
        ["ababa", "xyz", "abé"] * 700 + ["", NA, "abÉ"],
        ["ba", "yz", "bé"] * 700 + ["a", "a", "bé"],
        to=[-1] * 2103,
        case_insensitive=True,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_endswith_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
