import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_enc_detect

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_detect-python.txt")


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

eng = " ".join(["The quick brown fox jumps over the lazy dog."] * 8)
guess = stri_enc_detect(eng)["Encoding"][0]
OUT.write_text(
    f"stri_enc_detect on the English pangram repeated eight times guesses {guess} first.\n"
)
eng = " ".join(["The quick brown fox jumps over the lazy dog."] * 8)
def one():
    return stri_enc_detect([eng, "", NA])
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
