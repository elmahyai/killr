import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from png.readPNG import readPNG
from png.writePNG import writePNG

logo = Path(__file__).resolve().parents[1] / "png" / "img" / "Rlogo.png"


def one():
    img = readPNG(logo)
    raw = writePNG(img)
    img2 = readPNG(raw)
    identical = bool(np.array_equal(img, img2))
    diff = float(np.max(np.abs(np.asarray(img) - np.asarray(img2))))
    return [int(identical), diff]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
