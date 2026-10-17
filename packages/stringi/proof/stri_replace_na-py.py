import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA

from stringi.utils import stri_replace_na


long = ["test", NA] * 4000


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        first = stri_replace_na(["a", NA], ["x", "y"])
    return {
        "default": stri_replace_na(["test", NA]),
        "xx": stri_replace_na(["test", NA, ""], "xx"),
        "blank": stri_replace_na(["test", NA], ""),
        "na_repl": stri_replace_na(["a", NA], NA),
        "first": first,
        "long": stri_replace_na(long, "zz"),
    }

out = Path('/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_replace_na-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_replace_na(c("test", NA)) returns "test" and "NA".' + "\n", encoding="utf-8")


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
