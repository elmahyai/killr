import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_enc_isascii

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_isascii-python.txt")


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

shown = stri_enc_isascii(["abc", "ą"])
text = "stri_enc_isascii([\"abc\", \"ą\"]) returns " + ", ".join(
    "TRUE" if item else "FALSE" for item in shown
) + ".\n"
OUT.write_text(text)
def one():
    return {
        "text": stri_enc_isascii(["abc", "ą", "", NA, "NA", "a\x01b"]),
        "raw": stri_enc_isascii(bytes([65, 0, 127, 128])),
        "pieces": stri_enc_isascii([bytes([65, 66]), None, bytes([255]), b""]),
    }
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
