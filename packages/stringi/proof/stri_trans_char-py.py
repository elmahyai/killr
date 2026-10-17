import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.trans import stri_trans_char

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
        "dot": stri_trans_char(["id.123"], ".", "_"),
        "ab": stri_trans_char(["babaab"], "ab", "01"),
        "dup": stri_trans_char(["abc"], "aab", "XYZ"),
        "mismatch": stri_trans_char(["abc"], "abcd", "01"),
        "longer_rep": stri_trans_char(["aaa"], "a", "xy"),
        "na": stri_trans_char(["ab", NA, "NA"], "ab", "XY"),
        "na_pat": stri_trans_char(["ab", "cd"], NA, "X"),
        "na_rep": stri_trans_char(["ab"], "a", NA),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_trans_char-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_trans_char("id.123", ".", "_") returns id_123.' + "\n", encoding="utf-8")
