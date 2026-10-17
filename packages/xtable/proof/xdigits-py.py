import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import Xtable
from xtable.table_utils import RMatrix
from xtable.xdigits import xdigits


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable(
        [
            [a, b, c]
            for a, b, c in zip(range(1, n + 1), [i + 0.5 for i in range(1, n + 1)], "abcdef")
        ]
    )


def one():
    out = {}
    for i in range(6):
        x = make_xt(i)
        out[f"xdigits_{i}"] = xdigits(x)
        out[f"xdigits_zap_{i}"] = xdigits(x, zap=4)
    out["vec"] = xdigits([1.1, 2.22, 3])
    out["with_na"] = xdigits([1.5, float("nan"), 2.333])
    out["mat"] = xdigits(RMatrix([[1, 3.01], [2.5, 4]], nrow=2, ncol=2))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
