import json
import statistics
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from colorspace.diverging_hcl import diverging_hcl
from colorspace.hclplot import hclplot, hclplot_to_proof_dict
from colorspace.qualitative_hcl import qualitative_hcl
from colorspace.sequential_hcl import sequential_hcl

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def one():
    return {
        "qual": hclplot(qualitative_hcl(9, c=50, l=70), plot=False),
        "seq": hclplot(
            sequential_hcl(7, h=260, c=80, l=(35, 95), power=1),
            plot=False,
        ),
        "div": hclplot(
            diverging_hcl(7, h=(260, 0), c=80, l=(35, 95), power=1),
            plot=False,
        ),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

OUTPUT.mkdir(parents=True, exist_ok=True)
hclplot(
    qualitative_hcl(9, c=50, l=70),
    plot=False,
    save_path=str(OUTPUT / "hclplot-python.svg"),
)

payload = {key: hclplot_to_proof_dict(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
