import json
import statistics
import time
from pathlib import Path

from stringi._na import NA


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value



from stringi.sprintf import stri_string_format

example = stri_string_format("%.1f", 1.25)[0]
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_string_format-python.txt").write_text(
    f"stri_string_format('%.1f', 1.25) returns {example}.\n"
)


def one():
    return {
        "tenth": stri_string_format("%.1f", 1.25),
        "pad": stri_string_format("%05d", 7),
        "na": stri_string_format("%s", NA),
        "prec": stri_string_format("[%-10.3s]", "xxabcd"),
        "half": stri_string_format("%.0f", [1.5, 2.5]),
        "cjk": stri_string_format("[%10s]", "一", use_length=True),
        "bools": stri_string_format("%s %d", True, False),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
