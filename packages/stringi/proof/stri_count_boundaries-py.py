import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_count_boundaries


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_count_boundaries-python.txt").write_text(
    "stri_count_boundaries(\"A\\u0301\", type=\"character\") returns 1.\n",
    encoding="utf-8",
)


def one():
    text = [
        "The\u00a0above-mentioned features are very useful.",
        "A\u0301",
        "a\U0001f600b",
        "hello world\nnext",
        "",
        NA,
    ] * 40
    return [
        stri_count_boundaries(text, type="character"),
        stri_count_boundaries(text, type="word", skip_word_none=True),
        stri_count_boundaries(text, type="line"),
        stri_count_boundaries(text, type="sentence", locale="en_US"),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
