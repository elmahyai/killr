import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.print_xtable import print_xtable
from xtable.xtable_main import RDataFrame, xtable


def one():
    x = xtable(
        RDataFrame({"a": ["x&y", "z"], "b": ["p", "q"], "c": [3.141592653589793, 3.141592653589793]}),
        caption="Cap",
    )
    xnum = xtable(RDataFrame({"v": [1.2345, 1e5]}))
    from xtable.digits_replacement import digits_replacement

    digits_replacement(xnum, [0, 4])
    return {
        "latex": print_xtable(
            x,
            include_rownames=False,
            print_results=False,
            comment=False,
            timestamp=None,
            floating=False,
        ),
        "numeric": print_xtable(
            xnum,
            include_rownames=False,
            include_colnames=False,
            print_results=False,
            comment=False,
            timestamp=None,
            floating=False,
        ),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
