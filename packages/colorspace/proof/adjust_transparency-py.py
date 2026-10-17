import json
import statistics
import time

import numpy as np

from colorspace.adjust_transparency import adjust_transparency
from colorspace.desaturate import _PrismaticColors
from colorspace.lab import LAB

X = ["gray", "#BEBEBE", "#BEBEBE80"]
HEXES = ["#FF0000", "#00FF0080", "#336699", "#AABBCCDD"]
RGB_MAT = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype=np.float64)


def _json_vec(values):
    out = []
    for value in values:
        if value is None:
            out.append(None)
        elif isinstance(value, list):
            out.extend(_json_vec(value))
        else:
            out.append(str(value))
    return out


def one():
    lab_obj = LAB([[50, 40, 30], [60, -20, 50]], names=["a", "b"])
    bulk = [
        f"#{i:02X}{(255 - i):02X}{(i + 17) % 256:02X}" for i in range(256)
    ]
    prism = _PrismaticColors(["red", "blue", "#00FF0080"])
    return {
        "recycle_name": adjust_transparency("black", alpha=[0, 0.5, 1]),
        "recycle_hex": adjust_transparency("#000000", alpha=[0, 0.5, 1]),
        "recycle_palette": adjust_transparency([1, 2, 3], alpha=[0, 0.5, 1]),
        "null_alpha": adjust_transparency(X, alpha=None),
        "true_alpha": adjust_transparency(X, alpha=True),
        "false_alpha": adjust_transparency(X, alpha=False),
        "numeric_alpha": adjust_transparency(X, alpha=0.8),
        "hex_vector": adjust_transparency(HEXES, alpha=0.25),
        "named": adjust_transparency({"red": "#FF0000", "blue": "#0000FF80"}, alpha=True),
        "rgb_matrix": adjust_transparency(RGB_MAT, alpha=0.5),
        "lab_object": adjust_transparency(lab_obj, alpha=[0.2, 0.9]),
        "prismatic": adjust_transparency(prism, alpha=None),
        "bulk": adjust_transparency(bulk, alpha=True),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_vec(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
