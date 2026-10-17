import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_enc_detect2, stri_encode

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_detect2-python.txt")


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
    guess = stri_enc_detect2("hello")
OUT.write_text(
    f"stri_enc_detect2(\"hello\") guesses {guess['Encoding'][0]} with confidence {guess['Confidence'][0]:g}.\n"
)
pl = " ".join(["Zażółć gęślą jaźń."] * 8)
raw = bytes(stri_encode(pl, to="windows-1250", to_raw=True))
def one():
    return stri_enc_detect2([raw, b""], locale="pl")
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
