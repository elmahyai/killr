import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.trans import stri_trans_tolower

def show(item):
    if item is NA:
        return None
    if isinstance(item, list):
        return [show(part) for part in item]
    if isinstance(item, dict):
        return {key: show(value) for key, value in item.items()}
    return item



def one():
    return {
        "tr": stri_trans_tolower(["I", "i", "\u0130", "\u0131", NA, "NA", ""], "tr_TR"),
        "en": stri_trans_tolower(["I", "i"], "en_US"),
        "lt": stri_trans_tolower(["I\u0307"], "lt"),
        "el": stri_trans_tolower(["\u03a3\u03a3", "A\u03a3A"], "el"),
        "empty_locale": stri_trans_tolower(["i"], ""),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_trans_tolower-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_trans_tolower("I", "tr_TR") returns U+0131.' + "\n", encoding="utf-8")
