import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_count_words


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_count_words-python.txt").write_text(
    "stri_count_words(\"one two three\") returns 3.\n",
    encoding="utf-8",
)


def one():
    en = ["one two three", "above-mentioned", "123 456 abc", "", NA, "NA"] * 30
    return [
        stri_count_words(en),
        stri_count_words(["\u0e09\u0e31\u0e19\u0e01\u0e34\u0e19\u0e02\u0e49\u0e32\u0e27"] * 20, locale="th"),
        stri_count_words(["\u79c1\u306f\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u307e\u3059"] * 20, locale="ja"),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
