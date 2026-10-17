import json
import math
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.packet_panel_default import packet_panel_default


def one():
    layout = [2, 2, 1]
    condlevels = [[1, 2], [1, 2, 3]]
    p1 = packet_panel_default(layout, condlevels, 1, 1, 1, [False, True, False, False])
    p2 = packet_panel_default(layout, condlevels, 1, 2, 1, [False, True, False, False])
    p3 = packet_panel_default([2, 2, 2], condlevels, 2, 1, 1, [False], all_pages_skip=False)
    return list(p1) + list(p2) + list(p3)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
