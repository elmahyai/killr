import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_subset_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


found = stri_subset_fixed(["stringi R", "123", "ID456", ""], "1")
sentence = (
    'stri_subset_fixed(["stringi R", "123", "ID456", ""], "1") returns '
    + ", ".join(found)
    + "."
)

def one():
    return stri_subset_fixed(
        ["stringi R", "123", ""] * 700 + [NA, "Éva"],
        "i",
        omit_na=False,
        case_insensitive=True,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_subset_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
