import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_split_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


found = stri_split_fixed("a_b_c_d", "_")
sentence = 'stri_split_fixed("a_b_c_d", "_") returns ' + ", ".join(found[0]) + "."

def one():
    return stri_split_fixed(
        ["a_b_c__d"] * 600 + ["", NA],
        "_",
        n=[-1, 2, 4] * 200 + [-1, -1],
        omit_empty=False,
        tokens_only=True,
        simplify=False,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_split_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
