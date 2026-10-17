import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.trans import stri_trans_general

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
        "latin": stri_trans_general(["gro\u00df"], "Latin-ASCII"),
        "hex": stri_trans_general(["\u2620"], "Any-Hex"),
        "rev": stri_trans_general(["\\u0061\\u00df"], "Any-Hex", forward=False),
        "nfd": stri_trans_general(["\u0104"], "nfd; lower"),
        "rules": stri_trans_general(["abc"], "a > X; b > Y;", rules=True),
        "na": stri_trans_general(["A", NA, ""], "Latin-ASCII"),
        "na_id": stri_trans_general(["A", "B"], NA),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_trans_general-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_trans_general of groß with Latin-ASCII returns gross.' + "\n", encoding="utf-8")
