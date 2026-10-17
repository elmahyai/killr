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



from stringi.infix import s_plus

shown = ", ".join("NA" if item is NA else item for item in s_plus(["a", NA], ["b", "c"]))
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%s+%-python.txt").write_text(
    f"s_plus(['a', NA], ['b', 'c']) returns {shown}.\n"
)


def one():
    return {
        "id": s_plus("ID_", [1, 2, 3]),
        "na": s_plus(["a", NA], ["b", "c"]),
        "text": s_plus(["NA", NA], "x"),
        "empty": s_plus("", None),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
