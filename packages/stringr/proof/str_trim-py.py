import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.trim import str_trim


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


lines = [
    repr(str_trim("  String with trailing and leading white space\t")),
    repr(str_trim("\n\nString with trailing and leading white space\n\n")),
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_trim-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "both": str_trim("  String with trailing and leading white space\t"),
        "nl": str_trim("\n\nString with trailing and leading white space\n\n"),
        "left": str_trim(" abc ", "left"),
        "right": str_trim(" abc ", "right"),
        "nbsp": str_trim("\u00a0ab\u00a0"),
        "na": str_trim(["abc", NA]),
        "empty": str_trim([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
