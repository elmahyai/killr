import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA

from stringi.reverse import stri_reverse


base = [
    "123",
    "abc d e f",
    "ZXY (\u0105\u0104123$^).",
    NA,
    "",
    "\U0001f600b",
    "e\u0301",
    "a\u0328",
]
text = base + ["abc d e f"] * 4000


def one():
    return {"text": stri_reverse(text), "number": stri_reverse(123)}

out = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_reverse-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_reverse(c("123", "abc d e f")) returns "321" and "f e d cba".' + "\n", encoding="utf-8")


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
