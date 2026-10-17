import json
import statistics
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from colorspace.sequential_hcl import sequential_hcl
from colorspace.swatchplot import matrix_to_proof_dict, swatchplot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def one():
    return swatchplot(
        Hue=sequential_hcl(5, h=[0, 300], c=[60, 60], l=65),
        Chroma=sequential_hcl(5, h=0, c=[100, 0], l=65, rev=True, power=1),
        Luminance=sequential_hcl(5, h=260, c=[25, 25], l=[25, 90], rev=True, power=1),
        off=0,
        plot=False,
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

OUTPUT.mkdir(parents=True, exist_ok=True)
swatchplot(
    Hue=sequential_hcl(5, h=[0, 300], c=[60, 60], l=65),
    Chroma=sequential_hcl(5, h=0, c=[100, 0], l=65, rev=True, power=1),
    Luminance=sequential_hcl(5, h=260, c=[25, 25], l=[25, 90], rev=True, power=1),
    off=0,
    save_path=str(OUTPUT / "swatchplot-python.svg"),
)

payload = {"matrix": matrix_to_proof_dict(value), "median_ms": statistics.median(elapsed)}
print(json.dumps(payload))
