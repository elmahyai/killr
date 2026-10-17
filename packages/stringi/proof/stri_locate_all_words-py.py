import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_locate_all_words


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locate_all_words-python.txt").write_text(
    "stri_locate_all_words(\"ab cd\") starts at 1, 4.\n",
    encoding="utf-8",
)


def one():
    en = ["a\U0001f600bc def", "ab cd", "...", "", NA] * 25
    return [
        stri_locate_all_words(en),
        stri_locate_all_words(en, get_length=True),
        stri_locate_all_words(["\u79c1\u306f\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u307e\u3059"] * 15, locale="ja", get_length=True),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
