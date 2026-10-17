import contextlib
import io
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.coda_options import coda_options
from coda.display_coda_options import display_coda_options

root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)


def digest_lines(lines):
    return sum(sum(map(ord, line)) for line in lines)


def one(capture_path=None):
    coda_options(default=True)
    coda_options(frac1=0.12, digits=4)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        display_coda_options(stats=True, diags=True, plots=False)
    captured = buffer.getvalue().splitlines()
    if capture_path is not None:
        capture_path.write_text(buffer.getvalue())
    return [
        float(digest_lines(captured)),
        float(coda_options("frac1")),
        float(coda_options("digits")),
        float(coda_options("combine.stats")),
        float(len(captured)),
    ]


value = one(out_dir / "display.coda.options-python.txt")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "proof" / "display.coda.options-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
