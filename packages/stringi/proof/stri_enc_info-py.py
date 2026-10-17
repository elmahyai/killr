import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_enc_info

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_info-python.txt")


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

OUT.write_text(
    "stri_enc_info(\"UTF-8\") reports the friendly name "
    + stri_enc_info("UTF-8")["Name.friendly"]
    + ".\n"
)
def one():
    return [
        stri_enc_info("UTF-8"),
        stri_enc_info("ISO-8859-2"),
        stri_enc_info("US-ASCII"),
        stri_enc_info("UTF-16"),
    ]
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
