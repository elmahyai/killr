import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.trim import str_squish


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


lines = [
    repr(str_squish("  String with trailing,  middle, and leading white space\t")),
    repr(str_squish("\n\nString with excess,  trailing and leading white   space\n\n")),
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_squish-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "tabs": str_squish("ab\t\tc\t"),
        "middle": str_squish("  String with trailing,  middle, and leading white space\t"),
        "nl": str_squish("\n\nString with excess,  trailing and leading white   space\n\n"),
        "na": str_squish(NA),
        "empty": str_squish([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
