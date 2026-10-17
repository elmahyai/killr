import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.xtable_lsmeans import LSMeansFrame, xtable_lsmeans
from xtable.xtable_main import Factor


def one():
    xl = xtable_lsmeans(
        LSMeansFrame(
            {
                "est": [1, 2, 3],
                "trt": Factor(["a", "b", "a"], levels=["a", "b"]),
                "se": [0.1, 0.2, 0.3],
            },
            est_name="lsmean",
            mesg="note",
        ),
        caption="LS",
        label="tab:ls",
    )
    return {
        "class": list(xl.classes),
        "len": len(xl),
        "message": xl.attrs.get("message"),
        "sub1": xl.items[0].attrs.get("subheading"),
        "sub2": xl.items[1].attrs.get("subheading"),
        "ncol1": xl.items[0].ncol,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
