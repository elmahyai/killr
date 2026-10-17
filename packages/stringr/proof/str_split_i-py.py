import contextlib
import io
import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.split import str_split_i


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def example():
    fruits = [
        "apples and oranges and pears and bananas",
        "pineapples and mangos and guavas",
    ]
    print(str_split_i(fruits, " and ", 1))
    print(str_split_i(fruits, " and ", 4))
    print(str_split_i(fruits, " and ", -1))


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    example()
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_split_i-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(buf.getvalue(), encoding="utf-8")


def one():
    texts = ["1-2-3", "4-5", "only", NA, ""] * 80
    return [str_split_i(texts, "-", 2), str_split_i(texts, "-", -1)]


assert str_split_i(["a", "b-c"], "-", 2) == [NA, "c"]
assert str_split_i(["1-2-3", "4-5"], "-", -1) == ["3", "5"]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
