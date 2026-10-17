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



from stringi.sprintf import s_dollar

example = s_dollar("value='%d'", 3)[0]
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%s$%-python.txt").write_text(
    f"s_dollar('value=\'%d\'', 3) returns {example}.\n"
)


def one():
    return {
        "one": s_dollar("value='%d'", 3),
        "vec": s_dollar("value='%d'", [1, 2, 3]),
        "pair": s_dollar("%s=%d", (["a", "b"], [1, 2])),
        "na": s_dollar("%s", NA),
        "sci": s_dollar("%s", [1e5, 1e-4]),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
