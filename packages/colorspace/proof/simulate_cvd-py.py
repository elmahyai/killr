import json
import statistics
import time
from pathlib import Path

import numpy as np

from colorspace.deutanomaly_cvd import deutanomaly_cvd
from colorspace.interpolate_cvd_transform import interpolate_cvd_transform
from colorspace.lab import LAB
from colorspace.protanomaly_cvd import protanomaly_cvd
from colorspace.simulate_cvd import simulate_cvd
from colorspace.srgb import sRGB
from colorspace.tritanomaly_cvd import tritanomaly_cvd

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
EXAMPLE = ["#005000", "blue", "#00BB00"]
RGB_MAT = np.diag(np.ones(3)) * 255.0
WIDE = np.array(
    [[255, 0, 0], [0, 255, 0], [0, 0, 255], [128, 64, 32]],
    dtype=np.float64,
)
SRGB_OBJ = sRGB([1, 0, 0.25], [0, 1, 0.5], [0, 0, 0.75])
LAB_OBJ = LAB([50, 60, 70], [40, -20, 10], [30, 50, -40])
HEXES = ["#FF0000", "#00FF0080", "#336699", "#AABBCCDD"]
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
    tritan = tritanomaly_cvd()
    protan = protanomaly_cvd()
    deutan = deutanomaly_cvd()
    return {
        "example": simulate_cvd(EXAMPLE, tritan["6"]),
        "interpolated": simulate_cvd(
            EXAMPLE, interpolate_cvd_transform(tritan, severity=0.6)
        ),
        "hex": simulate_cvd("#33ab20", tritan["6"]),
        "named": simulate_cvd("red", deutan["8"]),
        "mixed": simulate_cvd(["green", "#ffc0cb"], protan["8"]),
        "alpha": simulate_cvd(HEXES, protan["10"]),
        "palette": simulate_cvd([1, 2, 3], tritan["4"]),
        "linear_false": simulate_cvd(
            ["#FF0000", "#800080", "#FFA500"], tritan["10"], linear=False
        ),
        "rgb_matrix": simulate_cvd(RGB_MAT, deutan["6"]),
        "wide": simulate_cvd(WIDE, protan["3"]),
        "srgb_object": simulate_cvd(SRGB_OBJ, tritan["6"]),
        "lab_object": simulate_cvd(LAB_OBJ, tritan["7"]),
        "lab_gamma": simulate_cvd(LAB_OBJ, tritan["7"], linear=False),
        "bulk": simulate_cvd(BULK, tritan["6"]),
    }


value = one()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "simulate_cvd-python.txt").write_text(
    "[1] " + " ".join(f'"{color}"' for color in value["example"]) + "\n",
    encoding="utf-8",
)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {
    "example": _json_vec(value["example"]),
    "interpolated": _json_vec(value["interpolated"]),
    "hex": _json_vec(value["hex"]),
    "named": _json_vec(value["named"]),
    "mixed": _json_vec(value["mixed"]),
    "alpha": _json_vec(value["alpha"]),
    "palette": _json_vec(value["palette"]),
    "linear_false": _json_vec(value["linear_false"]),
    "rgb_matrix": np.asarray(value["rgb_matrix"]).tolist(),
    "wide": np.asarray(value["wide"]).tolist(),
    "srgb_object": _json_color(value["srgb_object"]),
    "lab_object": _json_color(value["lab_object"]),
    "lab_gamma": _json_color(value["lab_gamma"]),
    "bulk": _json_vec(value["bulk"]),
    "median_ms": statistics.median(elapsed),
}
print(json.dumps(payload))
