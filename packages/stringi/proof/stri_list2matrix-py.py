import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA

from stringi.utils import stri_list2matrix


even = [["a", "b"], ["c", "d"], ["e", "f"]]
uneven = ["a", ["b", "c"]]
big = []
for i in range(1, 2001):
    if i % 2 == 0:
        big.append([f"a{i}", f"b{i}"])
    else:
        big.append([f"a{i}", NA])


def one():
    return {
        "even": stri_list2matrix(even),
        "even_byrow": stri_list2matrix(even, byrow=True),
        "uneven": stri_list2matrix(uneven),
        "uneven_fill": stri_list2matrix(uneven, fill=""),
        "uneven_nmin": stri_list2matrix(uneven, fill="", n_min=5),
        "byrow_nmin": stri_list2matrix(uneven, byrow=True, fill="", n_min=5),
        "by_row": stri_list2matrix([["a", "b"], ["c", "d"]], byrow=False, by_row=True),
        "by_row_off": stri_list2matrix([["a", "b"], ["c", "d"]], byrow=True, by_row=False),
        "numbers": stri_list2matrix([[1, 2], [True, False]]),
        "pad": stri_list2matrix([["a", "b"], "c"], n_min=4, fill="*"),
        "empty_nmin": stri_list2matrix([], n_min=2),
        "empty_byrow": stri_list2matrix([], n_min=2, byrow=True),
        "empty_cols": stri_list2matrix([[], []]),
        "big": stri_list2matrix(big, fill="*", n_min=3),
        "big_byrow": stri_list2matrix(big, byrow=True, fill="*", n_min=3),
    }

out = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_list2matrix-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_list2matrix(list(c("a", "b"), c("c", "d"), c("e", "f"))) returns rows (a, c, e) and (b, d, f).' + "\n", encoding="utf-8")


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
