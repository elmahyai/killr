import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.pad import stri_pad_both

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
        "odd": stri_pad_both(["ab"], 5, pad="*"),
        "even": stri_pad_both(["ab"], 6, pad="*"),
        "vec": stri_pad_both(["stringi"], list(range(8, 13)), pad="*"),
        "hangul": stri_pad_both(["\ud6c8\ubbfc\uc815\uc74c", "abcd"], width=10),
        "na": stri_pad_both(["a", NA], 4, pad="*"),
        "len": stri_pad_both(["a"], 4, use_length=True),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_pad_both-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_pad_both("ab", 5, "*") returns *ab**.' + "\n", encoding="utf-8")
