import json
import statistics
import time
from pathlib import Path

from colorspace.terrain_hcl import terrain_hcl

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "example12": terrain_hcl(12),
        "default7": terrain_hcl(7),
        "custom": terrain_hcl(9, h=(140, 20), c_=(70, 5), l=(55, 92), power=(0.15, 1.05)),
        "single": terrain_hcl(1),
        "empty": terrain_hcl(0),
        "alpha_vec": terrain_hcl(5, alpha=(1, 0.5, 0.25, 0.5, 1)),
        "alpha_scalar": terrain_hcl(4, alpha=0.75),
        "no_fixup": terrain_hcl(8, fixup=False),
        "bulk": terrain_hcl(256),
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
(OUTPUT / "terrain_hcl-python.txt").write_text("\n".join(value["example12"]) + "\n", encoding="utf-8")

print(json.dumps(payload))
