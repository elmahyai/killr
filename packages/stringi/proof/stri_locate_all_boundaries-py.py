import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_locate_all_boundaries


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locate_all_boundaries-python.txt").write_text(
    "stri_locate_all_boundaries(\"abc\", type=\"character\") starts at 1, 2, 3.\n",
    encoding="utf-8",
)


def one():
    text = ["a\U0001f600b", "A\u0301\U0001f468\u200d\U0001f469", "hello world\nnext", "", NA] * 20
    return [
        stri_locate_all_boundaries(text, type="character"),
        stri_locate_all_boundaries(text, type="character", get_length=True),
        stri_locate_all_boundaries(text, type="line"),
        stri_locate_all_boundaries(["", "..."], type="word", skip_word_none=True, omit_no_match=True, get_length=True),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
