import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.case import str_to_upper


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


dog = "The quick brown dog"
lines = [repr(str_to_upper(dog)), repr(str_to_upper("i")), repr(str_to_upper("i", "tr"))]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_to_upper-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "dog": str_to_upper("The quick brown dog"),
        "en": str_to_upper("i"),
        "tr": str_to_upper("i", "tr"),
        "vec": str_to_upper(["A", NA, "", "ß"]),
        "empty": str_to_upper([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
