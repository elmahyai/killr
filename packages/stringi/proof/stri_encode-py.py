import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_encode

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_encode-python.txt")


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

shown = stri_encode("ą", to="ISO-8859-2", to_raw=True)
OUT.write_text(
    f"stri_encode(\"ą\", to=\"ISO-8859-2\", to_raw=True) returns byte {shown[0]}.\n"
)
def one():
    return stri_encode(["ab", "ą", "€", NA], to="ISO-8859-2", to_raw=True)
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
