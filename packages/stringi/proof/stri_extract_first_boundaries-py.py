import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_extract_first_boundaries


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_extract_first_boundaries-python.txt").write_text(
    "stri_extract_first_boundaries(\"ab cd\", type=\"character\") returns a.\n",
    encoding="utf-8",
)


def one():
    text = ["hello world\nnext", "A\u0301b", "", NA, "  x"] * 30
    return [
        stri_extract_first_boundaries(text, type="character"),
        stri_extract_first_boundaries(text, type="word", skip_word_none=True),
        stri_extract_first_boundaries(text, type="line"),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
