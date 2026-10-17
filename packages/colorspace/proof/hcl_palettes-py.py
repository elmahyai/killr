import json
import statistics
import time
from pathlib import Path

from colorspace.hcl_palettes import catalog_to_proof_dict, hcl_palettes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"


def one():
    set2 = hcl_palettes(palette="Set 2")
    return {
        "qualitative": hcl_palettes(type="Qualitative"),
        "set2": set2,
        "mixed": hcl_palettes(type=["seq", "div"], palette=["blues", "tropic"]),
        "print_set2": repr(set2).splitlines(),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: catalog_to_proof_dict(val) if key != "print_set2" else val for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)

OUTPUT.mkdir(parents=True, exist_ok=True)
hcl_palettes(type="Qualitative", plot=True, n=7, save_path=str(OUTPUT / "hcl_palettes-python.svg"))
(OUTPUT / "hcl_palettes-set2-python.txt").write_text("\n".join(value["print_set2"]) + "\n", encoding="utf-8")

print(json.dumps(payload))
