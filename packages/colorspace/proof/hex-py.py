import json
import statistics
import time

import numpy as np

from colorspace.hex import hex as hex_color
from colorspace.hex2rgb import HexRGB
from colorspace.hsv import HSV
from colorspace.lab import LAB
from colorspace.rgb import RGB


def _json_vec(values):
    out = []
    for value in values:
        if value is None:
            out.append(None)
        else:
            out.append(str(value))
    return out


def one():
    hues = np.linspace(0, 360, 7)[:-1]
    hsv_obj = HSV(hues, 1, 1)
    srgb_obj = HexRGB(
        "sRGB",
        np.array([[1, 0, 0], [0, 1, 0], [0.25, 0.5, 0.75]], dtype=np.float64),
        None,
    )
    lab_obj = LAB(
        np.array([[50, 40, 30], [60, -20, 50], [70, 10, -40]], dtype=np.float64),
        names=["a", "b", "c"],
    )
    oog = RGB(2.0, -0.1, 0.5)
    bulk_hsv = HSV(np.linspace(0, 360, 256), 0.8, 0.9)
    return {
        "hsv_example": hex_color(hsv_obj),
        "srgb_object": hex_color(srgb_obj),
        "lab_named": hex_color(lab_obj),
        "fixup_true": hex_color(oog, fixup=True),
        "fixup_false": hex_color(oog, fixup=False),
        "bulk": hex_color(bulk_hsv),
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
