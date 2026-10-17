import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_split_boundaries


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_split_boundaries-python.txt").write_text(
    "stri_split_boundaries(\"hello world foo\", type=\"word\", skip_word_none=True, n=2) returns hello, world foo.\n",
    encoding="utf-8",
)


def one():
    text = ["one two three four", "hello world\nnext", "ab\ncd\r\nef"] * 20
    return [
        stri_split_boundaries(text, type="word", skip_word_none=True),
        stri_split_boundaries(text, type="word", skip_word_none=True, n=2),
        stri_split_boundaries(text, type="word", skip_word_none=True, n=2, tokens_only=True),
        stri_split_boundaries(text, type="line", skip_line_soft=True),
        stri_split_boundaries(["ab", "c"], n=3, type="character", simplify=True),
        stri_split_boundaries(["ab", "cd"], n=[1, NA], type="character"),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
