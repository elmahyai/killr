import json
import statistics
import time

import numpy as np

from colorspace.max_chroma import max_chroma


def _tolist(values):
    arr = np.asarray(values, dtype=np.float64).ravel()
    out = []
    for v in arr:
        if np.isnan(v):
            out.append(None)
        else:
            out.append(float(v))
    return out


def one():
    return {
        "example_h": max_chroma(h=np.arange(37) * 10, l=50),
        "example_l": max_chroma(h=120, l=np.arange(11) * 10),
        "floor_true": max_chroma(h=[0, 45, 90, 180], l=50, floor=True),
        "recycle": max_chroma(h=[0, 120, 240], l=[30, 50, 70, 90]),
        "wrap_h": max_chroma(h=[-30, 390, 720.5], l=50),
        "clamp_l": max_chroma(h=180, l=[-10, 0, 50, 100, 150]),
        "na_prop": max_chroma(h=[np.nan, 60], l=[50, np.nan]),
        "bulk": max_chroma(
            h=np.resize(np.arange(0, 360, 10), 512),
            l=np.resize(np.arange(5, 100, 5), 512),
        ),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _tolist(vals) for key, vals in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
