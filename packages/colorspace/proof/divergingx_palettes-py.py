import json
import statistics
import time
from pathlib import Path

from colorspace.divergingx_palettes import catalog_to_proof_dict, divergingx_palettes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def one():
    return {
        "all": divergingx_palettes(),
        "geyser": divergingx_palettes("Geyser"),
        "multi": divergingx_palettes(["geyser", "armyrose"]),
        "partial": divergingx_palettes("spec"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: catalog_to_proof_dict(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)

OUTPUT.mkdir(parents=True, exist_ok=True)
divergingx_palettes(plot=True, save_path=str(OUTPUT / "divergingx_palettes-python.svg"))

print(json.dumps(payload))
