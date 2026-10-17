import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_enc_get, stri_enc_set

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_set-python.txt")


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, bytes):
        return list(value)
    return value

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    previous = stri_enc_set("ISO-8859-2")
    stri_enc_set(previous)
OUT.write_text(
    f"stri_enc_set(\"ISO-8859-2\") returns {previous} because this ICU build keeps the default charset locked.\n"
)
def one():
    previous = stri_enc_set("ISO-8859-2")
    after = stri_enc_get()
    stri_enc_set(previous)
    return [previous, after]
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
