import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.print_xtable_matharray import print_xtable_matharray
from xtable.xtable_matharray import xtable_matharray


def one():
    x = xtable_matharray([[1, 3], [2, 4]])
    return print_xtable_matharray(
        x, print_results=False, comment=False, timestamp=None
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
