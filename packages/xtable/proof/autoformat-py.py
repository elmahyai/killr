import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.align import align
from xtable.autoformat import autoformat
from xtable.caption_replacement import Xtable
from xtable.digits import digits
from xtable.display import display


def one():
    out = {}
    for i in range(8):
        n = 2 + (i % 5)
        x = Xtable(
            [
                [idx, idx + i * 0.1, c]
                for idx, c in zip(range(1, n + 1), "abcdef"[:n])
            ]
        )
        y = autoformat(x, zap=5 + (i % 3))
        out[f"case_{i}"] = {
            "align": align(y),
            "digits": digits(y),
            "display": display(y),
        }
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
