import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.trans import stri_trans_list

def show(item):
    if item is NA:
        return None
    if isinstance(item, list):
        return [show(part) for part in item]
    if isinstance(item, dict):
        return {key: show(value) for key, value in item.items()}
    return item



def one():
    return stri_trans_list()

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_trans_list-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f"stri_trans_list() returns {len(stri_trans_list())} transforms and starts with {stri_trans_list()[0]}." + "\n", encoding="utf-8")
