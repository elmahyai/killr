import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.normalize import stri_trans_isnfkd


def one():
    return stri_trans_isnfkd(["\u03a9", "\u2126", NA, ""])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)


def show(item):
    if item is NA:
        return None
    if isinstance(item, list):
        return [show(part) for part in item]
    return item


print(json.dumps({"value": show(value), "median_ms": statistics.median(elapsed)}))

got = stri_trans_isnfkd("\u2126")
line = f"stri_trans_isnfkd of the ohm sign returns {got}."
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_trans_isnfkd-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(line + "\n", encoding="utf-8")
