import contextlib
import io
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.multi_menu import multi_menu

root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

sys.stdin = io.StringIO("1,3:5\n" * 21)
choices = ["alpha", "beta", "gamma", "delta", "epsilon"]


def one(capture_path=None):
    if capture_path is None:
        sink = open(os.devnull, "w", encoding="utf-8")
        close_sink = True
    else:
        sink = capture_path.open("w", encoding="utf-8")
        close_sink = True
    try:
        with contextlib.redirect_stdout(sink):
            selected = multi_menu(choices, "Pick variables", ["Id", "Name"])
    finally:
        if close_sink:
            sink.close()
    return [float(item) for item in selected]


value = one(out_dir / "multi.menu-python.txt")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
(root / "proof" / "multi.menu-py.txt").write_text(out + "\n")
print(out)
