import json
import statistics
import time

import numpy as np

from colorspace.deutan import deutan
from colorspace.hex2rgb import HexRGB


def _json_vec(values):
    out = []
    for value in values:
        if value is None:
            out.append(None)
        else:
            out.append(str(value))
    return out


def _json_color(color):
    return {
        "space": color.space,
        "names": None,
        "columns": list(color.columns),
        "coords": color.coords.tolist(),
    }


HEXES = ["#FF0000", "#00FF0080", "#336699", "#AABBCCDD"]
NAMED = {"red": "#FF0000", "blue": "#0000FF"}
RGB_MAT = np.diag(np.ones(3)) * 255.0
SRGB_OBJ = HexRGB(
    "sRGB",
    np.array([[1, 0, 0], [0, 1, 0], [0.25, 0.5, 0.75]], dtype=np.float64),
    None,
)
EXAMPLES = ["#005000", "blue", "#00BB00"]


def one():
    from colorspace.lab import LAB

    lab_obj = LAB(
        np.array([[50, 40, 30], [60, -20, 50], [70, 10, -40]], dtype=np.float64)
    )
    bulk = [f"#{i:02X}{(255 - i):02X}{(i + 17) % 256:02X}" for i in range(256)]
    return {
        "default": deutan(HEXES),
        "severity": deutan(HEXES, severity=0.6),
        "zero": deutan(HEXES, severity=0),
        "named": deutan(NAMED),
        "colors": deutan(["red", "blue", "darkgreen"]),
        "palette": deutan([1, 2, 3]),
        "rgb_matrix": deutan(RGB_MAT),
        "srgb_object": deutan(SRGB_OBJ),
        "lab_object": deutan(lab_obj),
        "linear_false": deutan(["#FF0000", "#800080", "#FFA500"], linear=False),
        "examples": deutan(EXAMPLES),
        "bulk": deutan(bulk),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {
    "default": _json_vec(value["default"]),
    "severity": _json_vec(value["severity"]),
    "zero": _json_vec(value["zero"]),
    "named": _json_vec(value["named"]),
    "colors": _json_vec(value["colors"]),
    "palette": _json_vec(value["palette"]),
    "rgb_matrix": np.asarray(value["rgb_matrix"]).tolist(),
    "srgb_object": _json_color(value["srgb_object"]),
    "lab_object": _json_color(value["lab_object"]),
    "linear_false": _json_vec(value["linear_false"]),
    "examples": _json_vec(value["examples"]),
    "bulk": _json_vec(value["bulk"]),
    "median_ms": statistics.median(elapsed),
}
print(json.dumps(payload))
