import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_locate_last_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


loc = stri_locate_last_fixed("ababa", "aba")
sentence = f'stri_locate_last_fixed("ababa", "aba") starts at {loc[0][0]} and ends at {loc[0][1]}.'

def one():
    return stri_locate_last_fixed(
        ["ababa", "agAGA"] * 800 + ["", NA, "zzz"],
        ["aba", "aga"] * 800 + ["a", "a", "q"],
        case_insensitive=True,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locate_last_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
