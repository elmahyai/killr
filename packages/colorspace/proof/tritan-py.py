import json
import statistics
import time
from pathlib import Path

import numpy as np

from colorspace.lab import LAB
from colorspace.srgb import sRGB
from colorspace.tritan import tritan

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
HEXES = ["#FF0000", "#00FF0080", "#336699", "#AABBCCDD"]
NAMED = {"red": "#FF0000", "blue": "#0000FF"}
RGB_MAT = np.diag(np.ones(3)) * 255.0
SRGB_OBJ = sRGB([1, 0, 0.25], [0, 1, 0.5], [0, 0, 0.75])
LAB_OBJ = LAB([50, 60, 70], [40, -20, 10], [30, 50, -40])
EXAMPLE = ["#005000", "blue", "#00BB00"]
BULK = [f"#{i:02X}{(255 - i):02X}{(i + 17) % 256:02X}" for i in range(256)]


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def _json_color(color):
    return {
        "space": color.space,
        "names": None,
        "columns": list(color.columns),
        "coords": color.coords.tolist(),
    }


def one():
    return {
        "default": tritan(HEXES),
        "severity": tritan(HEXES, severity=0.6),
        "zero": tritan(HEXES, severity=0),
        "named": tritan(NAMED),
        "colors": tritan(["red", "blue", "darkgreen"]),
        "palette": tritan([1, 2, 3]),
        "rgb_matrix": tritan(RGB_MAT),
        "srgb_object": tritan(SRGB_OBJ),
        "lab_object": tritan(LAB_OBJ),
        "linear_false": tritan(["#FF0000", "#800080", "#FFA500"], linear=False),
        "example": tritan(EXAMPLE, severity=0.6),
        "bulk": tritan(BULK),
    }


value = one()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "tritan-python.txt").write_text(
    "[1] " + " ".join(f'"{color}"' for color in value["example"]) + "\n",
    encoding="utf-8",
)

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
    "example": _json_vec(value["example"]),
    "bulk": _json_vec(value["bulk"]),
    "median_ms": statistics.median(elapsed),
}
print(json.dumps(payload))
