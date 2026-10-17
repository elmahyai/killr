import json
import statistics
import time
from pathlib import Path

from stringi.datetime import stri_datetime_symbols

shown = stri_datetime_symbols("en_US")["Month"][0]
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_symbols-python.txt"
).write_text(f'stri_datetime_symbols("en_US")$Month[1] is {shown}.\n')


def one():
    return {
        "en": stri_datetime_symbols("en_US"),
        "pl": stri_datetime_symbols("pl_PL", context="format", width="wide"),
        "he": stri_datetime_symbols("@calendar=hebrew"),
        "narrow": stri_datetime_symbols("en_US", width="narrow"),
        "ja": stri_datetime_symbols("@calendar=japanese", width="narrow")["Era"],
        "th": stri_datetime_symbols("th_TH_TRADITIONAL")["Era"],
        "ja_trad": stri_datetime_symbols("ja_JP_TRADITIONAL", width="narrow")["Era"],
        "coptic": stri_datetime_symbols("@calendar=coptic")["Month"],
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
