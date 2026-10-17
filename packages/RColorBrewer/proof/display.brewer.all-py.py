import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from RColorBrewer.brewer import display_brewer_all


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)


def one():
    drawn = display_brewer_all(draw=True)
    plt.close(drawn["figure"])
    return drawn["rgb"] + drawn["usr"]


drawn = display_brewer_all(draw=True)
drawn["figure"].savefig(OUT / "display.brewer.all-python.svg", format="svg")
plt.close(drawn["figure"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
