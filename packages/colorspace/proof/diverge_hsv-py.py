import json
import statistics
import time
from pathlib import Path

from colorspace.diverge_hsv import diverge_hsv

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "example7": diverge_hsv(7),
        "custom": diverge_hsv(9, h=(200, 40), s=0.85, v=0.95, power=1.15),
        "single": diverge_hsv(1),
        "empty": diverge_hsv(0),
        "alpha_vec": diverge_hsv(7, alpha=(1, 0.5, 0.25, 0.5, 1, 1, 1)),
        "alpha_scalar": diverge_hsv(4, alpha=0.75),
        "no_fixup": diverge_hsv(8, fixup=False),
        "bulk": diverge_hsv(256),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_vec(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)

OUTPUT.mkdir(parents=True, exist_ok=True)
(OUTPUT / "diverge_hsv-python.txt").write_text("\n".join(value["example7"]) + "\n", encoding="utf-8")

print(json.dumps(payload))
