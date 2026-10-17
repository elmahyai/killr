import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA

from stringi.escape import stri_escape_unicode


ascii_text = "".join(chr(code) for code in range(1, 128))
mix = "A \t\n\"'\\\u00e9\U0001f600"
data = [
    ascii_text,
    "é©ÿ",
    "aą!",
    "😀",
    mix,
    NA,
    "",
] + ["aą!", "😀", NA, ""] * 2000


def one():
    return stri_escape_unicode(data)

out = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_escape_unicode-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_escape_unicode("aą!") returns the ASCII text a\\u0105!.' + "\n", encoding="utf-8")


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
