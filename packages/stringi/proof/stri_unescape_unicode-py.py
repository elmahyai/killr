import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA

from stringi.escape import stri_unescape_unicode


samples = [
    "a\\u0105!\\u0032\\n",
    "\\a\\b\\t\\n\\v\\f\\r\\\"\\'",
    "\\e\\?",
    "\\x41\\x4",
    "\\101",
    "\\x{1F600}",
    "\\x{0001F600}",
    "\\U0001F600",
    "\\u12",
    "\\",
    "\\q",
    "\\cA",
    "\\c",
    "plain",
    "",
    "\\uD800\\uDC00",
    NA,
]
data = samples + ["a\\u0105!\\u0032\\n"] * 3000


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return stri_unescape_unicode(data)

out = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_unescape_unicode-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_unescape_unicode("a\\u0105!\\u0032\\n") returns "aą!2" followed by a newline.' + "\n", encoding="utf-8")


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
