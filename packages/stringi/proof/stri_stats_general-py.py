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



from stringi.stats import stri_stats_general

s = [
    "Lorem ipsum dolor sit amet, consectetur adipisicing elit.",
    "nibh augue, suscipit a, scelerisque sed, lacinia in, mi.",
    "Cras vel lorem. Etiam pellentesque aliquet tellus.",
    "",
]
x = stri_stats_general(s)
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_stats_general-python.txt").write_text(
    f"stri_stats_general(s)['Lines'] returns {x['Lines']} and Chars returns {x['Chars']}.\n"
)


def one():
    return {
        "lorem": stri_stats_general(s),
        "na": stri_stats_general(["a", NA, "  ", "\u00a0b"]),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
