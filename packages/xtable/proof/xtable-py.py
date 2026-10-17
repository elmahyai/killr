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
from xtable.xtable_main import RDataFrame, xtable


def message_of(expr):
    try:
        return expr()
    except ValueError as exc:
        return str(exc)


def plain(value):
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    df = RDataFrame(
        {
            "a": [1, 2, 3],
            "b": [4, 5, 6],
            "c": ["a", "b", "c"],
            "d": [True, False, True],
            "e": [1, 1, 1],
        }
    )
    x = xtable(df)
    out = {
        "align": align(x),
        "digits": digits(x),
        "display": display(x),
        "class": list(x.classes),
        "logical_col": [row[3] for row in x.data],
        "ncol": [x.ncol],
        "nrow": [x.nrow],
    }
    x2 = xtable(
        RDataFrame({"a": [1, 2], "b": [3, 4]}),
        caption="Cap",
        label="tab:1",
        align=["l", "l", "l"],
        digits=[0, 1, 1],
        display=["s", "d", "f"],
    )
    out["custom"] = {
        "caption": caption(x2),
        "label": label(x2),
        "align": align(x2),
        "digits": digits(x2),
        "display": display(x2),
    }
    xm = xtable([[1, 2, 3], [4, 5, 6]])
    out["matrix"] = {
        "class": list(xm.classes),
        "ncol": [xm.ncol],
        "names": xm.col_names,
        "align": align(xm),
        "digits": digits(xm),
        "display": display(xm),
    }

    class foo:
        pass

    out["err_class"] = [message_of(lambda: xtable(foo()))]
    repeated = []
    for j in range(1, 201):
        n = 2 + (j % 3)
        xt = xtable(
            RDataFrame(
                {"a": list(range(1, n + 1)), "b": list(range(1, n + 1))}
            )
        )
        repeated.extend(align(xt))
        repeated.extend(str(v) for v in digits(xt))
        repeated.extend(display(xt))
    out["repeated"] = repeated
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
