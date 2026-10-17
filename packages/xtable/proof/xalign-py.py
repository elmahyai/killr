import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import Xtable
from xtable.table_utils import RMatrix
from xtable.xalign import xalign


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable(
        [[a, b, c] for a, b, c in zip(range(1, n + 1), range(1, n + 1), "abcdef")]
    )


def one():
    out = {}
    for i in range(6):
        x = make_xt(i)
        out[f"xalign_{i}"] = xalign(x)
        out[f"xalign_nopad_{i}"] = xalign(x, pad=False)
    out["vec_num"] = xalign([1, 2, 3.5])
    out["vec_chr"] = xalign(["a", "b"])
    out["mat"] = xalign(
        RMatrix([[1, 3, 5], [2, 4, 6]], nrow=2, ncol=3)
    )
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
