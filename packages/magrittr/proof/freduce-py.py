import json
import math
import statistics
import time
from pathlib import Path

from magrittr.fseq import freduce

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)


def one():
    return freduce(16, [math.sqrt, math.log])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
(out / "freduce-python.txt").write_text("freduce(16, [math.sqrt]) returns 4.\n")
