import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_extract_all_words


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_extract_all_words-python.txt").write_text(
    "stri_extract_all_words(\"one two\") returns one, two.\n",
    encoding="utf-8",
)


def one():
    en = ["stringi: THE string processing package 123.48...", "above-mentioned", "...", "", NA] * 20
    return [
        stri_extract_all_words(en),
        stri_extract_all_words(["\u0e09\u0e31\u0e19\u0e01\u0e34\u0e19\u0e02\u0e49\u0e32\u0e27"] * 15, locale="th"),
        stri_extract_all_words(["\u79c1\u306f\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u307e\u3059"] * 15, locale="ja"),
        stri_extract_all_words(["a b", "c"], simplify=True),
        stri_extract_all_words(["...", NA], omit_no_match=True),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
