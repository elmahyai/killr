import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import colorspace.choose_palette as choose_palette_mod
from colorspace.diverging_hcl import diverging_hcl
from colorspace.sequential_hcl import sequential_hcl
from colorspace.rainbow_hcl import rainbow_hcl


def _stub_tcl(pal=diverging_hcl, n=7, parent=None, **kwargs):
    return pal(n)


def _stub_shiny(pal=None, n=7, **kwargs):
    return pal(n)


choose_palette_mod.choose_palette_tcltk = _stub_tcl
choose_palette_mod.choose_palette_shiny = _stub_shiny

from colorspace.choose_palette import choose_palette  # noqa: E402

OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "choose_palette-python.txt").write_text(
    "\n".join(diverging_hcl(7)) + "\n", encoding="utf-8"
)


def one():
    return {
        "default_tcl": choose_palette(gui="tcltk"),
        "seq_shiny": choose_palette(sequential_hcl, 5, gui="shiny"),
        "rainbow_tcl": choose_palette(rainbow_hcl, 6, gui="tcltk"),
        "custom_n": choose_palette(diverging_hcl, 11, gui="shiny"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
payload = {key: [str(v) for v in val] for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
