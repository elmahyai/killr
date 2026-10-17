import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_enc_fromutf32

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_fromutf32-python.txt")


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

shown = stri_enc_fromutf32([65, 261])
OUT.write_text(f"stri_enc_fromutf32([65, 261]) returns {shown}.\n")
def one():
    return stri_enc_fromutf32([[65, 261], None, [], [NA], [0], [0x110000], [0xD800]])
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
