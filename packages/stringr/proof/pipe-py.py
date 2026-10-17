import json
import statistics
import time
from pathlib import Path

from stringr.pipe import pipe

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "%>%-python.txt").write_text(
    str(pipe(2, lambda value: value + 3, lambda value: value * 4)) + "\n"
)


def one():
    return pipe(2, lambda value: value + 3, lambda value: value * 4)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
