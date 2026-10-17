import contextlib
import io
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.read_and_check import read_and_check

root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

sys.stdin = io.StringIO("0.25\n" * 21)


def one(capture_path=None):
    if capture_path is None:
        sink = open(os.devnull, "w", encoding="utf-8")
    else:
        sink = capture_path.open("w", encoding="utf-8")
    try:
        with contextlib.redirect_stdout(sink):
            value = read_and_check(
                "Enter a probability", lower=0, upper=1, default=0.5
            )
    finally:
        sink.close()
    return [float(value)]


value = one(out_dir / "read.and.check-python.txt")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
(root / "proof" / "read.and.check-py.txt").write_text(out + "\n")
print(out)
