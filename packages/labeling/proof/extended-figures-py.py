import json
import statistics
import time
from pathlib import Path

import matplotlib.pyplot as plt

from labeling.ticks import extended_figures


output = Path("packages/labeling/docs/output/extended-figures-python.png")
output.parent.mkdir(parents=True, exist_ok=True)


def one():
    extended_figures(samples=10)
    figures = [plt.figure(number) for number in plt.get_fignums()]
    if figures:
        figures[-2].savefig(output)
    plt.close("all")
    return None


value = one()
one_time = []
for _ in range(20):
    started = time.perf_counter()
    one()
    one_time.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "value": value,
    "median_ms": statistics.median(one_time),
    "output": str(output),
}))
