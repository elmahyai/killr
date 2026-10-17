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



from stringi.locale import stri_locale_list

example = len(stri_locale_list())
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locale_list-python.txt").write_text(
    f"len(stri_locale_list()) returns {example}.\n"
)


def one():
    return stri_locale_list()

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
