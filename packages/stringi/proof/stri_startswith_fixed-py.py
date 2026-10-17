import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_startswith_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


found = stri_startswith_fixed(["a1", "a2", "b3", "a4", "c5"], "a")
sentence = (
    'stri_startswith_fixed(["a1", "a2", "b3", "a4", "c5"], "a") returns '
    + ", ".join(str(item) for item in found)
    + "."
)

def one():
    return stri_startswith_fixed(
        ["a1", "ba", "éab"] * 700 + ["", NA, "Ébc"],
        ["a", "b", "ab"] * 700 + ["a", "a", "éb"],
        from_=[1, 1, 2] * 700 + [1, 1, 1],
        case_insensitive=True,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_startswith_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
