import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.encoding import stri_conv

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_conv-python.txt")


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

shown = stri_conv(bytes([0xB1]), from_="ISO-8859-2", to="UTF-8")
OUT.write_text(
    f"stri_conv(bytes([0xb1]), from_=\"ISO-8859-2\", to=\"UTF-8\") returns {shown}.\n"
)
def one():
    return {
        "utf16": stri_conv("ab", to="UTF-16BE", to_raw=True),
        "latin": stri_conv(bytes([0xB1]), from_="ISO-8859-2", to="UTF-8"),
    }
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
