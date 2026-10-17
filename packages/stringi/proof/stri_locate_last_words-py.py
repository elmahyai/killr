import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_locate_last_words


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locate_last_words-python.txt").write_text(
    "stri_locate_last_words(\"hello world\") starts at 7.\n",
    encoding="utf-8",
)


def one():
    text = ["hello world", "hello ", "a\U0001f600bc def", "...", "", NA] * 30
    return [
        stri_locate_last_words(text),
        stri_locate_last_words(text, get_length=True),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
