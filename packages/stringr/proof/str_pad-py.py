import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.pad import str_pad


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


lines = [
    repr([
        str_pad("hadley", 30, "left"),
        str_pad("hadley", 30, "right"),
        str_pad("hadley", 30, "both"),
    ]),
    repr(str_pad(["a", "abc", "abcdef"], 10)),
    repr(str_pad("a", [5, 10, 20])),
    repr(str_pad("a", 10, pad=["-", "_", " "])),
    repr(str_pad("hadley", 3)),
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_pad-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "left": str_pad("had", 10, "left"),
        "right": str_pad("had", 10, "right"),
        "both": str_pad("had", 10, "both"),
        "vec": str_pad(["a", "abc", "abcdef"], 10),
        "widths": str_pad("a", [5, 10, 20]),
        "pads": str_pad("a", 10, pad=["-", "_", " "]),
        "short": str_pad("hadley", 3),
        "cjk": str_pad("\u4e2d", 6, "both"),
        "length": str_pad("\u4e2d", 5, "both", use_width=False),
        "na": str_pad(["a", NA], [3, NA]),
        "empty": str_pad([], 10)
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
