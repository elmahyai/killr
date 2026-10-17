import json
import statistics
import time
from pathlib import Path

from colorspace.rainbow_hcl import rainbow_hcl
from colorspace.sequential_hcl import sequential_hcl
from colorspace.specplot import _r_rainbow, specplot, specplot_to_proof_dict

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def one():
    x = sequential_hcl(50, "Blues 3")
    y = sequential_hcl(50, "Reds 3")
    return {
        "blues": specplot(x, plot=False),
        "compare": specplot(x, y=y, rgb=True, plot=False),
        "rainbow_hcl100": specplot(rainbow_hcl(100), fix=True, plot=False),
        "na_tail": specplot([*x[:10], None], plot=False),
        "nofix": specplot(rainbow_hcl(10), fix=False, plot=False),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: specplot_to_proof_dict(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)

OUTPUT.mkdir(parents=True, exist_ok=True)
specplot(_r_rainbow(100), rgb=True, save_path=str(OUTPUT / "specplot-python.svg"))

print(json.dumps(payload))
