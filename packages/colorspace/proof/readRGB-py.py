import json
import statistics
import time
from pathlib import Path

from colorspace.readrgb import readRGB

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"
FIXTURE = ROOT / "proof" / "fixtures" / "sample.rgb"


def _json_color(color):
    names = None if color.names is None else list(color.names)
    columns = [] if color.coords.size == 0 else list(color.columns)
    return {
        "space": color.space,
        "names": names,
        "columns": columns,
        "coords": color.coords.tolist(),
    }


def one():
    path = str(FIXTURE)
    return {
        "rgb": readRGB(path),
        "hsv": readRGB(path, "HSV"),
        "lab": readRGB(path, "LAB"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_color(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)

OUTPUT.mkdir(parents=True, exist_ok=True)
(OUTPUT / "readRGB-python.txt").write_text(
    str(value["rgb"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload))
