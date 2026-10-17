import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.pad import stri_pad_left

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
        "hash": stri_pad_left(["stringi"], 10, pad="#"),
        "wide": stri_pad_left(["\u1100"], 4),
        "use_length": stri_pad_left(["\u1100"], 4, use_length=True),
        "mark": stri_pad_left(["x"], 3, pad="a\u0301"),
        "na": stri_pad_left(["a", NA, "NA"], [4, 3, 4], pad="."),
        "short": stri_pad_left(["abcd"], 2),
        "float": stri_pad_left(["a"], 3.9, pad="*"),
        "neg": stri_pad_left(["a"], -3, pad="*"),
        "recycle": stri_pad_left(["a", "b", "c"], [3, 4], pad="*"),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_pad_left-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_pad_left("stringi", 10, "#") returns ###stringi.' + "\n", encoding="utf-8")
