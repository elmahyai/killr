import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_extract_all_boundaries


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_extract_all_boundaries-python.txt").write_text(
    "stri_extract_all_boundaries(\"a b\", type=\"word\", skip_word_none=True) returns a, b.\n",
    encoding="utf-8",
)


def one():
    text = ["123 456 abc", "a\U0001f600b", "", NA] * 25
    return [
        stri_extract_all_boundaries(text, type="word", skip_word_none=True),
        stri_extract_all_boundaries(text, type="word", skip_word_number=True),
        stri_extract_all_boundaries(text, type="word", skip_word_letter=True),
        stri_extract_all_boundaries(text, type="character"),
        stri_extract_all_boundaries(text, type="word", skip_word_none=True, omit_no_match=True),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
