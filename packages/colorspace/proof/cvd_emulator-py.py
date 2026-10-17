import json
import statistics
import sys
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PNG_ROOT = ROOT.parent / "png"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PNG_ROOT))

import colorspace.cvd_emulator as cvd_mod

from png.writePNG import writePNG  # noqa: E402


def _stub_app(file=None, overwrite=False, shiny_trace=False):
    return {"mode": "shiny", "shiny.trace": bool(shiny_trace)}


OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)
work = OUT / "cvd_emulator-work"
work.mkdir(parents=True, exist_ok=True)
input_path = work / "sample.png"

flat = np.array(
    [1, 0, 0, 1] * 4
    + [0, 1, 0, 1] * 4
    + [0, 0, 1, 1] * 4
    + [1, 1, 0, 1] * 4,
    dtype=np.float64,
)
sample = flat.reshape((4, 4, 4), order="F")
writePNG(sample, target=input_path)

from colorspace.cvd_emulator import cvd_emulator  # noqa: E402

with redirect_stdout(StringIO()):
    cvd_emulator(input_path, overwrite=True)

from png.readPNG import readPNG  # noqa: E402

summaries = []
for kind in ("deutan", "protan", "tritan", "desaturate"):
    path = work / f"{kind}_{input_path.name}"
    summaries.append(float(np.sum(readPNG(path))))

(OUT / "cvd_emulator-python.txt").write_text(
    "\n".join(f"{kind}: {value:.6f}" for kind, value in zip(
        ("deutan", "protan", "tritan", "desaturate"), summaries, strict=True
    ))
    + "\n",
    encoding="utf-8",
)


def one():
    return {
        "shiny": _stub_app(shiny_trace=True),
        "summaries": summaries,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {
    "shiny_mode": 1,
    "shiny_trace": value["shiny"]["shiny.trace"],
    "summaries": value["summaries"],
    "median_ms": statistics.median(elapsed),
}
print(json.dumps(payload))
