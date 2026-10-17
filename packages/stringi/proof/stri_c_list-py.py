import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA
from stringi.join import stri_c_list

items = [["a", NA], [], ["", "b"]] + [["k", str(i)] for i in range(1, 4001)]


def one():
    return {
        "rows": stri_c_list(items, sep="-"),
        "collapsed": stri_c_list(items, sep="-", collapse="|"),
    }

out = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_c_list-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("stri_c_list(list(c(\"a\", \"b\"), character(0), c(\"c\", NA)), sep = \"-\") returns c(\"a-b\", NA).\n", encoding="utf-8")


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
