import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.coda_options import coda_options

root = Path(__file__).resolve().parent


def one():
    coda_options(default=True)
    x = np.array([1.2, 2.3, 3.4, 100, 200, 0.5, np.nan, 4.5], dtype=np.float64)
    bw0 = coda_options("bandwidth")(x)
    coda_options(digits=4, trace=False, frac1=0.15)
    coda_options(digits=2)
    multi = coda_options("gr.bin", "gr.max")
    return [
        float(coda_options("digits")),
        float(coda_options("trace")),
        float(coda_options("frac1")),
        float(bw0),
        *[float(v) for v in coda_options("quantiles")],
        float(multi["gr.bin"]),
        float(multi["gr.max"]),
        float(coda_options("combine.stats")),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "coda.options-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
