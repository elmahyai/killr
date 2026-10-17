import contextlib
import io
import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringr.split import str_split_fixed


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
    print(str_split_fixed(fruits, " and ", 3))
    print(str_split_fixed(fruits, " and ", 4))


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    example()
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_split_fixed-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(buf.getvalue(), encoding="utf-8")


def one():
    fruits = [
        "apples and oranges and pears and bananas",
        "pineapples and mangos and guavas",
    ]
    texts = (fruits + ["one and two", NA]) * 125
    return str_split_fixed(texts, " and ", 4)


assert str_split_fixed(["a", "a-b"], "-", 2) == [["a", ""], ["a", "b"]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
