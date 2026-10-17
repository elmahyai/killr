import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.align import align
from xtable.caption import caption
from xtable.digits import digits
from xtable.display import display
from xtable.label import label
from xtable.xtable_matharray import xtable_matharray


def plain(value):
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            return [plain(row) for row in value]
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    m = [[1.0, 3.0, 5.0, 7.0], [2.0, 4.0, 6.0, 8.0]]
    x = xtable_matharray(m, caption="Var", label="eq:vcov")
    return {
        "class": list(x.classes),
        "nrow": [x.nrow],
        "ncol": [x.ncol],
        "align": align(x),
        "digits": digits(x),
        "display": display(x),
        "caption": caption(x),
        "label": label(x),
        "data": [
            [int(v) if isinstance(v, float) and v.is_integer() else v for v in row]
            for row in x.data
        ],
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
