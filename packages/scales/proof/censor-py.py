import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scales.bounds import censor

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "censor-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
shown = censor([float("-inf"), -1, 0.5, 1, 2, None, float("inf")])
out.write_text(repr(shown) + "\n", encoding="utf-8")


def one():
    return censor([float("-inf"), -1, 0.5, 1, 2, None, float("inf")])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
