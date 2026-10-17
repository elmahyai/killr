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



from stringi.locale import stri_locale_get, stri_locale_info, stri_locale_set

example = stri_locale_info("pl_PL")["Name"]
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locale_info-python.txt").write_text(
    f"stri_locale_info('pl_PL')['Name'] returns {example}.\n"
)


def one():
    previous = stri_locale_get()
    try:
        stri_locale_set("pl_PL")
        return {
            "pl": stri_locale_info("pl_PL"),
            "mixed": stri_locale_info("Pl_pL"),
            "c": stri_locale_info("C"),
            "cutf": stri_locale_info("c.UTF-8"),
            "utf": stri_locale_info("en_US.UTF-8"),
            "phone": stri_locale_info("fr_FR@collation=phonebook"),
            "keywords": stri_locale_info("@collation=phonebook"),
            "zh": stri_locale_info("zh_Hant_TW"),
            "empty": stri_locale_info(""),
            "null": stri_locale_info(None),
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
