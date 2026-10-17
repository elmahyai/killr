import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmap.is_key_missing import is_key_missing
from fastmap.key_missing import key_missing

root = Path(__file__).resolve().parent
package = root.parent


def one():
    x = key_missing()
    text = str(x)
    return [
        1.0 if is_key_missing(x) else 0.0,
        1.0 if x == key_missing() else 0.0,
        float(len(text)),
        *[float(ord(ch)) for ch in text],
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "key_missing-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)

x = key_missing()
example = (
    f"{x}\n"
    f"is {'TRUE' if is_key_missing(x) else 'FALSE'}\n"
    f"identical {'TRUE' if x == key_missing() else 'FALSE'}\n"
)
(package / "docs" / "output" / "key_missing-python.txt").write_text(example)
