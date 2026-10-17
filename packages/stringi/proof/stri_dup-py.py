import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA
from stringi.join import stri_dup

text = ["abcdefghij"] * 16000 + [NA, "", "NA", "x"]
times = [3, 0, -1, 2]


def one():
    return stri_dup(text, times)

out = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_dup-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("stri_dup(c(\"a\", NA), 2) returns c(\"aa\", NA).\n", encoding="utf-8")


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
