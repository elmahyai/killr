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



from stringi.infix import stri_plus

shown = ", ".join("NA" if item is NA else item for item in stri_plus(["a", NA], ["b", "c"]))
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%stri+%-python.txt").write_text(
    f"stri_plus(['a', NA], ['b', 'c']) returns {shown}.\n"
)


def one():
    return {
        "id": stri_plus("ID_", [1, 2, 3]),
        "na": stri_plus(["a", NA], ["b", "c"]),
        "text": stri_plus(["NA", NA], "x"),
        "empty": stri_plus("", None),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
