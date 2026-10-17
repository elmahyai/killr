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



from stringi.locale import stri_locale_get, stri_locale_set

previous = stri_locale_get()
stri_locale_set("pl_PL")
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locale_get-python.txt").write_text(
    f"stri_locale_get() returns {stri_locale_get()}.\n"
)
stri_locale_set(previous)


def one():
    previous_locale = stri_locale_get()
    try:
        stri_locale_set("pl_PL")
        return stri_locale_get()
    finally:
        stri_locale_set(previous_locale)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
