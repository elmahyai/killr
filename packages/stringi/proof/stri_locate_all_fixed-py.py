import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.fixed import stri_locate_all_fixed


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


loc = stri_locate_all_fixed(
    "abababa", "ABA", case_insensitive=True, overlap=True
)[0]
starts = ", ".join(str(row[0]) for row in loc)
sentence = (
    'stri_locate_all_fixed("abababa", "ABA", case_insensitive=True, overlap=True) finds starts '
    + starts
    + "."
)

def one():
    return stri_locate_all_fixed(
        ["abababa"] * 200 + ["aaa"] * 200 + ["", NA, "zzz"],
        ["ABA"] * 200 + ["aa"] * 200 + ["a", "a", "a"],
        omit_no_match=False,
        case_insensitive=True,
        overlap=True,
    )


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locate_all_fixed-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
