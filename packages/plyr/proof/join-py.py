import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plyr.join import join

n = 20000
xid = [(i % 4000) + 1 for i in range(n)]
xv = [(i + 1) * 0.5 for i in range(n)]
yid = [(i % 4000) + 501 for i in range(n)]
yv = [(i + 1) * 0.25 for i in range(n)]
frame_x = {"id": xid, "xv": xv}
frame_y = {"id": yid, "yv": yv}


def one():
    return join(frame_x, frame_y, by="id")


def show(value):
    if value is None:
        return "NA"
    return float(value).hex()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

parts = []
for ident, left, right in zip(value.columns["id"], value.columns["xv"], value.columns["yv"]):
    parts.append(f"{int(ident)}|{show(left)}|{show(right)}")
print("VALUE " + ";".join(parts))
print(f"MS {statistics.median(elapsed):.17g}")
