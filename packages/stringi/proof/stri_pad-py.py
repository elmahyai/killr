import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.pad import stri_pad

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
        "left": stri_pad(["ab"], 5),
        "right": stri_pad(["ab"], 5, "r"),
        "both": stri_pad(["ab"], 5, "b"),
        "choices": stri_pad(["a"], 3, ["left", "right", "both"]),
        "na": stri_pad(["a", NA], [3, 4], pad=["*", NA]),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_pad-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_pad("ab", 5, "both") returns *ab**.' + "\n", encoding="utf-8")
