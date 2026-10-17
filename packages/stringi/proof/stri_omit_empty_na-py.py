import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA

from stringi.utils import stri_omit_empty_na


x = ["a", NA, "", "b", " "]
long = x * 4000


def one():
    return {"example": stri_omit_empty_na(x), "long": stri_omit_empty_na(long)}

out = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_omit_empty_na-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_omit_empty_na(c("a", NA, "", "b")) returns "a" and "b".' + "\n", encoding="utf-8")


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
