import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.boundary import stri_split_lines


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_split_lines-python.txt").write_text(
    "stri_split_lines(\"a\\nb\") returns a, b.\n",
    encoding="utf-8",
)


def one():
    text = ["a\n", "a\n\n", "a\r\nb\r\n", "a\vb\fc\u0085d\u2028e\u2029f", "", NA] * 30
    return [
        stri_split_lines(text),
        stri_split_lines(text, omit_empty=True),
        stri_split_lines(["a\n\nb", "c\n", "\n"], omit_empty=[NA, False, True]),
    ]

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
