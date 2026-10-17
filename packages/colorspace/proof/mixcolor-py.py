import json
import statistics
import time
import warnings

import numpy as np

from colorspace.hex2rgb import HexRGB
from colorspace.hsv import HSV
from colorspace.lab import LAB
from colorspace.luv import LUV
from colorspace.mixcolor import mixcolor
from colorspace.rgb import RGB
from colorspace.xyz import XYZ
from colorspace._cspace_convert import PolarLUVColor


def _block(color):
    names = None if color.names is None else list(color.names)
    columns = [] if color.coords.size == 0 else list(color.columns)
    return {
        "space": color.space,
        "names": names,
        "columns": columns,
        "coords": color.coords.tolist(),
    }


def one():
    red = HexRGB("sRGB", np.array([[1.0, 0.0, 0.0]]), None)
    green = HexRGB("sRGB", np.array([[0.0, 1.0, 0.0]]), None)
    bulk_a = HexRGB(
        "sRGB",
        np.column_stack(
            [
                np.linspace(0, 1, 256),
                np.zeros(256),
                1.0 - np.linspace(0, 1, 256),
            ]
        ),
        None,
    )
    bulk_b = HexRGB(
        "sRGB",
        np.column_stack(
            [
                np.zeros(256),
                np.linspace(0, 1, 256),
                np.linspace(0, 1, 256),
            ]
        ),
        None,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return {
            "example": mixcolor(0.5, red, green),
            "rgb": mixcolor(0.25, RGB(1, 0, 0), RGB(0, 0, 1)),
            "lab": mixcolor(0.5, LAB(50, 50, 0), LAB(50, -50, 0)),
            "hsv": mixcolor(0.5, HSV(0, 1, 1), HSV(120, 1, 1)),
            "polarluv": mixcolor(
                0.3,
                PolarLUVColor(np.array([[50.0, 80.0, 0.0]]), None),
                PolarLUVColor(np.array([[50.0, 80.0, 180.0]]), None),
            ),
            "where_xyz": mixcolor(0.5, red, green, where="XYZ"),
            "where_luv": mixcolor(0.5, LUV(50, 0, 0), LUV(50, 10, -10)),
            "recycle_alpha": mixcolor([0.25, 0.5, 0.75], red, green),
            "recycle_colors": mixcolor(
                0.5,
                HexRGB(
                    "sRGB",
                    np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
                    None,
                ),
                green,
            ),
            "bulk": mixcolor(np.linspace(0, 1, 256), bulk_a, bulk_b),
        }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _block(color) for key, color in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
