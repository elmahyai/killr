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



from stringi.infix import stri_times

example = stri_times("ab", 3)[0]
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%stri*%-python.txt").write_text(
    f"stri_times('ab', 3) returns {example}.\n"
)


def one():
    return {
        "rep": stri_times("ab", 3),
        "na": stri_times(["a", NA], 2),
        "seq": stri_times("a", [1, 2, 3, 4, 5]),
        "text": stri_times(["NA", NA], 2),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
