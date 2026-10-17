import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA
from stringi.join import stri_join

left = list(range(1, 15997)) + [NA, 7, 8, 9]
right = ["a", "b", "NA", ""]


def one():
    return {
        "rows": stri_join(left, right, sep="-"),
        "collapsed": stri_join(left, right, sep="-", collapse="|"),
        "empty": stri_join(left, [], "z"),
        "ignored": stri_join([], ["a", "b"], ignore_null=True),
    }

out = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_join-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("stri_join(1:3, c(\"a\", \"b\", \"c\"), sep = \"-\") returns c(\"1-a\", \"2-b\", \"3-c\").\n", encoding="utf-8")


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
