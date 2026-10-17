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



from stringi.info import stri_info
from stringi.locale import stri_locale_get, stri_locale_set

example = stri_info(False)["ICU.version"]
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_info-python.txt").write_text(
    f"stri_info(False)['ICU.version'] returns {example}.\n"
)


def one():
    previous = stri_locale_get()
    try:
        stri_locale_set("pl_PL")
        info = stri_info(False)
        return {
            "unicode": info["Unicode.version"],
            "icu": info["ICU.version"],
            "system": info["ICU.system"],
            "utf8": info["ICU.UTF8"],
            "internal": info["Charset.internal"],
            "native": info["Charset.native"],
            "locale": info["Locale"]["Name"],
            "short": stri_info(True),
        }
    finally:
        stri_locale_set(previous)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
