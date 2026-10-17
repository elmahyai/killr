import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.case import str_to_title


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


dog = "The quick brown dog"
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_to_title-python.txt").write_text(repr(str_to_title(dog)) + "\n", encoding="utf-8")


def one():
    return {
        "dog": str_to_title("The quick brown dog"),
        "tr": str_to_title("istanbul", "tr"),
        "vec": str_to_title(["a", NA, ""]),
        "empty": str_to_title([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
