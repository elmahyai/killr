import json
import statistics
import time
from pathlib import Path

from colorspace.heat_hcl import heat_hcl

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "example12": heat_hcl(12),
        "default7": heat_hcl(7),
        "custom": heat_hcl(9, h=(20, 100), c_=(90, 20), l=(40, 85), power=(0.3, 1.1)),
        "single": heat_hcl(1),
        "empty": heat_hcl(0),
        "alpha_vec": heat_hcl(5, alpha=(1, 0.5, 0.25, 0.5, 1)),
        "alpha_scalar": heat_hcl(4, alpha=0.75),
        "no_fixup": heat_hcl(8, fixup=False),
        "bulk": heat_hcl(256),
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
(OUTPUT / "heat_hcl-python.txt").write_text("\n".join(value["example12"]) + "\n", encoding="utf-8")

print(json.dumps(payload))
