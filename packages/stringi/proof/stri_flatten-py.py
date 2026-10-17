import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA
from stringi.join import stri_flatten

src = ["ab", "", NA, "NA"] * 8000


def one():
    return {
        "dropped": stri_flatten(src, collapse="|", na_empty=True, omit_empty=True),
        "kept": stri_flatten(src, collapse="|", na_empty=NA),
        "missing": stri_flatten(src, collapse="|"),
        "empty": stri_flatten([], collapse=","),
    }

out = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_flatten-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("stri_flatten(c(NA, \"\", \"A\", \"\", \"B\", NA, \"C\"), collapse = \",\", na_empty = TRUE, omit_empty = TRUE) returns \"A,B,C\".\n", encoding="utf-8")


def _jsonable(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": _jsonable(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
