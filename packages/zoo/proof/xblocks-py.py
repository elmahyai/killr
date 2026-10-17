import math
import statistics
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.plot import xblocks
from zoo.series import Zoo


def fmt_one(value):
    if value is None:
        return "NA"
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    number = float(value)
    if math.isnan(number):
        return "NA"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(number, ".16g")


def fmt_vec(value):
    return "|".join(fmt_one(item) for item in list(value))


def block_text(name, rec):
    border = rec["border"]
    return "\n".join(
        [
            f"CASE {name}",
            "left=" + fmt_vec(rec["left"]),
            "right=" + fmt_vec(rec["right"]),
            "bottom=" + fmt_one(rec["bottom"]),
            "top=" + fmt_one(rec["top"]),
            "col=" + fmt_vec(rec["col"]),
            "border=" + ("NA" if border is None else str(border)),
        ]
    )


def one():
    flow = Zoo(np.array([1, np.nan, 3, 3, np.nan, 8], dtype=float), [1, 2, 3, 4, 5, 6])
    flat = Zoo(np.repeat(10.0, 6), [1, 2, 3, 4, 5, 6])
    flags = Zoo(np.arange(1, 6, dtype=float), [1, 2, 3, 4, 5])
    parts = [
        block_text("coverage", xblocks(flow, col="darkgray", ybottom=0, height=2, draw=False)),
        block_text(
            "function",
            xblocks(
                flat,
                lambda t: np.asarray(t) > 3,
                col="gray",
                ybottom=0,
                ytop=1,
                border="slategray",
                draw=False,
            ),
        ),
        block_text(
            "logical-y",
            xblocks(
                flags,
                [True, True, False, False, True],
                col=["red", "blue"],
                ybottom=0,
                ytop=2,
                draw=False,
            ),
        ),
    ]
    return "\n\n".join(parts)


value = one()
out = "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/xblocks-python.txt"
with open(out, "w", encoding="utf-8") as handle:
    handle.write(value + "\n")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

flow = Zoo(np.array([1, np.nan, 3, 3, np.nan, 8], dtype=float), [1, 2, 3, 4, 5, 6])
drawn = xblocks(flow, col="darkgray", ybottom=0, ytop=10, draw=True)
axis = drawn["axes"]
axis.plot([1, 2, 3, 4, 5, 6], [1, np.nan, 3, 3, np.nan, 8], color="black", linewidth=1.5)
axis.set_ylabel("flow")
drawn["figure"].savefig(
    "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/xblocks-python.svg",
    format="svg",
)
plt.close(drawn["figure"])
print("%.17g" % statistics.median(elapsed))
