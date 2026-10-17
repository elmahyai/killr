import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_split_lines1


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_split_lines1-python.txt").write_text(
    "stri_split_lines1(\"a\\nb\\n\") returns a, b.\n",
    encoding="utf-8",
)


def one():
    return [
        stri_split_lines1("a\nb\n"),
        stri_split_lines1("a\n\n"),
        stri_split_lines1("a\r\nb\r\n"),
        stri_split_lines1("a\n\rb"),
        stri_split_lines1("a\vb\fc\u0085d\u2028e\u2029f\r"),
        stri_split_lines1(""),
        stri_split_lines1("\n"),
        stri_split_lines1(NA),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
