import json
import statistics
import time
from pathlib import Path

from colorspace.darken import darken

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"

CL = ["#CDE4F3", "#E7F3D3", "#F7F0C7", "#EFCFE5", "#D0D1E7"]
HEXES = ["#FF0000", "#00FF0080", "#336699", "#AABBCCDD"]


def one():
    bulk = [f"#{i:02X}{(255 - i):02X}{(i + 17) % 256:02X}" for i in range(256)]
    return {
        "default": darken(CL, 0.15),
        "hcl": darken(CL, 0.15, space="HCL"),
        "hls": darken(CL, 0.15, space="HLS"),
        "deep": darken(CL, 0.3),
        "absolute": darken(HEXES, 0.2, method="absolute"),
        "zero": darken(["#112233", "#445566"], [0.2, 0]),
        "recycle": darken("#112233", [0.1, 0.2, 0.3]),
        "negative": darken(CL, -0.1),
        "named": darken({"red": "#FF0000", "blue": "#0000FF"}),
        "palette": darken([1, 2, 3], 0.25),
        "no_fixup": darken(["#FF0000", "#010101"], 0.5, fixup=False),
        "bulk": darken(bulk, 0.12),
    }


def time_median(f):
    f()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        f()
        elapsed.append((time.perf_counter() - started) * 1000)
    return statistics.median(elapsed)


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


value = one()
payload = {key: _json_vec(val) for key, val in value.items()}
payload["median_ms"] = time_median(one)
print(json.dumps(payload))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "darken-python.txt").write_text("\n".join(darken(CL, 0.15)) + "\n", encoding="utf-8")
