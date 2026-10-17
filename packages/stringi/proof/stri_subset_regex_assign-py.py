import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.subset import stri_subset_regex_assign


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


text = ["stringi R", "123", "ID456", "", NA] * 400
found = stri_subset_regex_assign(
    ["stringi R", "123", "ID456", ""], "[0-9]+$", negate=True, value=NA
)
shown = ", ".join("NA" if item is NA else item for item in found)
sentence = (
    '`stri_subset_regex<-`(["stringi R", "123", "ID456", ""], "[0-9]+$", '
    "negate=True, value=NA) returns " + shown + "."
)
out = Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_subset_regex<--python.txt"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(sentence + "\n", encoding="utf-8")


def one():
    return stri_subset_regex_assign(text, "[0-9]+", value="N")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(
    json.dumps(
        {"value": canon(value), "median_ms": statistics.median(elapsed)},
        ensure_ascii=False,
        separators=(",", ":"),
    )
)
