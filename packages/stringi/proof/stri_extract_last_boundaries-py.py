import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_extract_last_boundaries


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_extract_last_boundaries-python.txt").write_text(
    "stri_extract_last_boundaries(\"hello world\", type=\"word\", skip_word_none=True) returns world.\n",
    encoding="utf-8",
)


def one():
    text = ["hello world", "hello ", "...", "ab\ncd", "", NA] * 30
    return [
        stri_extract_last_boundaries(text, type="character"),
        stri_extract_last_boundaries(text, type="word", skip_word_none=True),
        stri_extract_last_boundaries(text, type="line"),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
