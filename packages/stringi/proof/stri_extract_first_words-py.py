import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_extract_first_words


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_extract_first_words-python.txt").write_text(
    "stri_extract_first_words(\"hello world\") returns hello.\n",
    encoding="utf-8",
)


def one():
    text = ["hello world", "  x", "", NA, "123 abc"] * 40
    return [
        stri_extract_first_words(text),
        stri_extract_first_words(["\u79c1\u306f\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u307e\u3059"] * 20, locale="ja"),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
