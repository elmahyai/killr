import contextlib
import io
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.coda_options import coda_options
from coda.codamenu import codamenu

root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

sys.stdin = io.StringIO("3\n" * 21)


def one(capture_path=None):
    if capture_path is None:
        sink = open(os.devnull, "w", encoding="utf-8")
    else:
        sink = capture_path.open("w", encoding="utf-8")
    try:
        with contextlib.redirect_stdout(sink):
            codamenu()
    finally:
        sink.close()
    return [
        float(coda_options("digits")),
        float(coda_options("trace")),
        float(coda_options("frac1")),
    ]


value = one(out_dir / "codamenu-python.txt")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "proof" / "codamenu-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
