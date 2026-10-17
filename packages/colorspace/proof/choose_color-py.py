import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import colorspace.choose_color as choose_color_mod
import colorspace.hcl_color_picker as picker_mod


def _stub_picker(shiny_trace=False):
    return {"color": "#336699", "shiny.trace": bool(shiny_trace)}


picker_mod.hcl_color_picker = _stub_picker
choose_color_mod.hcl_color_picker = _stub_picker

from colorspace.choose_color import choose_color  # noqa: E402

OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "choose_color-python.txt").write_text("#336699\n", encoding="utf-8")


def one():
    return {
        "default": choose_color(),
        "traced": choose_color(shiny_trace=True),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {
    "default_color": value["default"]["color"],
    "default_trace": value["default"]["shiny.trace"],
    "traced_color": value["traced"]["color"],
    "traced_trace": value["traced"]["shiny.trace"],
    "median_ms": statistics.median(elapsed),
}
print(json.dumps(payload))
