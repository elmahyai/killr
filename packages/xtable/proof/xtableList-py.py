import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.align import align
from xtable.digits import digits
from xtable.display import display
from xtable.xtable_list import RList, xtable_list


def one():
    from xtable.xtable_main import RDataFrame

    x = RList(
        [
            RDataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}),
            [[7, 8], [9, 10]],
        ],
        subheadings=["Part A", "Part B"],
        message=["note", ""],
    )
    xl = xtable_list(x, caption="List cap", label="tab:list")
    return {
        "class": list(xl.classes),
        "len": len(xl),
        "caption": xl.attrs.get("caption"),
        "label": xl.attrs.get("label"),
        "message": xl.attrs.get("message"),
        "sub1": xl.items[0].attrs.get("subheading"),
        "sub2": xl.items[1].attrs.get("subheading"),
        "align1": align(xl.items[0]),
        "digits1": digits(xl.items[0]),
        "display1": display(xl.items[0]),
        "nrow2": xl.items[1].nrow,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
